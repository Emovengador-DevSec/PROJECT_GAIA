"""Moderated, coarse-grained citizen reports. Pending text is never returned publicly."""

from __future__ import annotations

import base64
import re
import secrets
import sqlite3
from collections import OrderedDict
from contextlib import closing
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Literal

from PIL import Image, ImageOps
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from .community import GEOD

KINDS = Literal["fire", "landslide", "dry_water", "crop_damage"]
CELL_DEGREES = 0.005
LIMIT = 3
WINDOW_SECONDS = 3600
HISTORY: OrderedDict[str, tuple[float, int]] = OrderedDict()
LOCK = Lock()
MAX_PHOTO_BYTES = 2 * 1024 * 1024
MAX_PHOTO_ENCODED = 4 * ((MAX_PHOTO_BYTES + 2) // 3)
PHOTO_LICENSE = "https://creativecommons.org/licenses/by/4.0/"


class ReportPhotoIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    author: str = Field(min_length=2, max_length=80, pattern=r"^[^@\r\n<>]+$")
    consent: Literal[True]
    base64: str = Field(min_length=4, max_length=MAX_PHOTO_ENCODED)


class ReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    kind: KINDS
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    observed_at: AwareDatetime
    note: str = Field(max_length=280, default="")
    photo: ReportPhotoIn | None = None

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
    db.execute("PRAGMA foreign_keys=ON")
    db.execute(
        """CREATE TABLE IF NOT EXISTS reports (
          id TEXT PRIMARY KEY, kind TEXT NOT NULL, lon REAL NOT NULL, lat REAL NOT NULL,
          observed_at TEXT NOT NULL, note TEXT NOT NULL, status TEXT NOT NULL
        )""",
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS report_photos (
          report_id TEXT PRIMARY KEY REFERENCES reports(id) ON DELETE CASCADE,
          author TEXT NOT NULL, image BLOB NOT NULL
        )""",
    )
    return db


def prepare_photo(encoded: str) -> bytes:
    try:
        original = base64.b64decode(encoded, validate=True)
        if len(original) > MAX_PHOTO_BYTES:
            raise ValueError
        with Image.open(BytesIO(original), formats=("JPEG", "PNG", "WEBP")) as source:
            if source.width * source.height > 20_000_000 or getattr(source, "is_animated", False):
                raise ValueError
            oriented = ImageOps.exif_transpose(source)
            oriented.thumbnail((1600, 1600))
            # Copy only pixels so EXIF, GPS and any original comments are removed.
            clean = Image.new("RGB", oriented.size)
            clean.paste(oriented.convert("RGB"))
            output = BytesIO()
            clean.save(output, format="JPEG", quality=85)
            return output.getvalue()
    except (ValueError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Adjunta una foto JPG, PNG o WebP de hasta 2 MB y 20 megapíxeles.") from exc


def create(path: Path, report: ReportIn) -> str:
    ident = secrets.token_hex(16)
    lon, lat = (round(round(value / CELL_DEGREES) * CELL_DEGREES, 3) for value in (report.lon, report.lat))
    image = prepare_photo(report.photo.base64) if report.photo else None
    with closing(_open(path)) as db, db:
        db.execute(
            "INSERT INTO reports VALUES (?, ?, ?, ?, ?, ?, 'pending')",
            (ident, report.kind, lon, lat, report.observed_at.isoformat(timespec="minutes"), report.note),
        )
        if report.photo and image is not None:
            db.execute("INSERT INTO report_photos VALUES (?, ?, ?)", (ident, report.photo.author, image))
    return ident


def list_reports(path: Path, status: Literal["pending", "visible"]) -> list[dict]:
    if not path.is_file():
        return []
    with closing(_open(path)) as db:
        rows = db.execute(
            "SELECT r.id, r.kind, r.lon, r.lat, r.observed_at, r.note, p.author FROM reports r "
            "LEFT JOIN report_photos p ON p.report_id=r.id WHERE r.status=? ORDER BY r.rowid DESC LIMIT 100",
            (status,),
        )
        records = [dict(row) for row in rows]
        for record in records:
            author = record.pop("author")
            if author:
                prefix = "/api/reports" if status == "visible" else "/api/reports/moderation"
                record["photo"] = {
                    "author": author, "license": "CC BY 4.0", "license_url": PHOTO_LICENSE,
                    "image_url": f"{prefix}/{record['id']}/photo",
                }
            if status == "visible":
                record.pop("note")
        return records


def get_photo(path: Path, ident: str, status: Literal["pending", "visible"]) -> bytes | None:
    if not re.fullmatch(r"[a-f0-9]{32}", ident) or not path.is_file():
        return None
    with closing(_open(path)) as db:
        row = db.execute(
            "SELECT p.image FROM report_photos p JOIN reports r ON r.id=p.report_id "
            "WHERE r.id=? AND r.status=?",
            (ident, status),
        ).fetchone()
    return row["image"] if row else None


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
