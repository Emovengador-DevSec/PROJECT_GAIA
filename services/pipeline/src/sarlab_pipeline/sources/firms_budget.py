"""Persist historical FIRMS reservations before every HTTP attempt, including failures."""
from __future__ import annotations

import json
import time

import httpx

from .. import settings as S
from ..ingest import _ingest_lock, _write_json


def wait_for_remote_budget(key: str, *, ceiling: int = 3500, client: httpx.Client | None = None) -> None:
    """Use NASA's shared-account counter; its actual cost can exceed days requested."""
    while True:
        try:
            get = client.get if client else httpx.get
            response = get("https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/",
                           params={"MAP_KEY": key}, timeout=30)
            response.raise_for_status()
            status = response.json()
            current = int(status["current_transactions"])
            maximum = int(status["transaction_limit"])
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise RuntimeError("No se pudo verificar la cuota de NASA FIRMS. Reintenta más tarde.") from None
        if current < min(ceiling, maximum - 500):
            return
        time.sleep(30)


def reserve(days: int, *, limit: int = 3500, window: int = 610) -> None:
    if not 1 <= days <= 5 or limit < days:
        raise ValueError("Reserva FIRMS inválida.")
    S.CATALOG.mkdir(parents=True, exist_ok=True)
    path = S.CATALOG / "firms-transactions.json"
    while True:
        try:
            with _ingest_lock():
                now = time.time()
                records = json.loads(path.read_text()) if path.exists() else []
                records = [row for row in records if now - row["at"] < window]
                if sum(row["days"] for row in records) + days <= limit:
                    _write_json(path, [*records, {"at": now, "days": days}])
                    return
                wait = min(30, max(.1, min(row["at"] for row in records) + window - now))
        except RuntimeError:
            wait = .1  # Another ingestion/reservation owns the short catalogue lock.
        time.sleep(wait)
