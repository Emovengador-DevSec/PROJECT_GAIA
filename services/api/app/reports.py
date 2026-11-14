"""Moderated, coarse-grained citizen reports. Pending text is never returned publicly."""

from __future__ import annotations

import re
import secrets
import sqlite3
from collections import OrderedDict
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from .community import GEOD

KINDS = Literal["fire", "landslide", "dry_water", "crop_damage"]
CELL_DEGREES = 0.005
LIMIT = 3
WINDOW_SECONDS = 3600
HISTORY: OrderedDict[str, tuple[float, int]] = OrderedDict()
LOCK = Lock()


class ReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    kind: KINDS
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    observed_at: AwareDatetime
    note: str = Field(max_length=280, default="")

    @field_validator("note")
    @classmethod
    def no_contact(cls, value: str) -> str:
        if re.search(r"@|https?://|www\.|(?:\+?\d[ .()-]*){7}", value, re.IGNORECASE):
            raise ValueError("La nota no debe incluir enlaces ni información de contacto.")
        return value

    @field_validator("observed_at")
    @classmethod
    def within_window(cls, value: datetime) -> datetime:
        now = datetime.now(UTC)
        if not now - timedelta(days=30) <= value <= now:
            raise ValueError("Indica una fecha de observación de los últimos 30 días.")
        return value.astimezone(UTC)


def allow_submission(host: str) -> bool:
    now = monotonic()
    with LOCK:
        while HISTORY and next(iter(HISTORY.values()))[0] + WINDOW_SECONDS <= now:
            HISTORY.popitem(last=False)
        if host not in HISTORY and len(HISTORY) >= 4096:
            return False
        start, count = HISTORY.get(host, (now, 0))
        if count >= LIMIT:
            return False
        HISTORY[host] = start, count + 1
        return True


def _open(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute(
        """CREATE TABLE IF NOT EXISTS reports (
          id TEXT PRIMARY KEY, kind TEXT NOT NULL, lon REAL NOT NULL, lat REAL NOT NULL,
          observed_at TEXT NOT NULL, note TEXT NOT NULL, status TEXT NOT NULL
        )""",
    )
    return db


def create(path: Path, report: ReportIn) -> str:
    ident = secrets.token_hex(16)
    lon, lat = (round(round(value / CELL_DEGREES) * CELL_DEGREES, 3) for value in (report.lon, report.lat))
    with closing(_open(path)) as db, db:
        db.execute(
            "INSERT INTO reports VALUES (?, ?, ?, ?, ?, ?, 'pending')",
            (ident, report.kind, lon, lat, report.observed_at.isoformat(timespec="minutes"), report.note),
        )
    return ident


def list_reports(path: Path, status: Literal["pending", "visible"]) -> list[dict]:
    if not path.is_file():
        return []
    with closing(_open(path)) as db:
        rows = db.execute(
            "SELECT id, kind, lon, lat, observed_at, note FROM reports "
            "WHERE status=? ORDER BY rowid DESC LIMIT 100",
            (status,),
        )
        records = [dict(row) for row in rows]
        if status == "visible":
            for record in records:
                record.pop("note")
        return records


def moderate(path: Path, ident: str, action: Literal["visible", "rejected"]) -> bool:
    if not path.is_file():
        return False
    with closing(_open(path)) as db, db:
        if action == "rejected":
            update = db.execute(
                "DELETE FROM reports WHERE id=? AND status IN ('pending', 'visible')", (ident,)
            )
        else:
            update = db.execute(
                "UPDATE reports SET status='visible', note='' WHERE id=? AND status='pending'",
                (ident,),
            )
        return update.rowcount == 1


def annotate(reports: list[dict], fires: list[dict], hv_areas: list) -> list[dict]:
    from shapely.geometry import Point

    detections = [
        (feature["geometry"]["coordinates"][:2], datetime.fromisoformat(feature["properties"]["date"]))
        for feature in fires
    ]
    for item in reports:
        stamp = datetime.fromisoformat(item["observed_at"])
        item["firms_match"] = item["kind"] == "fire" and any(
            abs(stamp - when) <= timedelta(hours=24)
            and GEOD.inv(item["lon"], item["lat"], *coordinates)[2] <= 2000
            for coordinates, when in detections
        )
        point = Point(item["lon"], item["lat"])
        item["nisar_overlap"] = any(area.covers(point) for area in hv_areas)
    return reports
