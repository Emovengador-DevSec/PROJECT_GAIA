"""Archive MODIS Standard Processing observations in five-day NASA FIRMS CSV files."""
from __future__ import annotations

import csv
import io
import os
import time
from datetime import date, timedelta

import httpx
from dotenv import load_dotenv

from sarlab_pipeline import settings as S
from sarlab_pipeline.ingest import load_catalog
from sarlab_pipeline.sources.firms_budget import reserve, wait_for_remote_budget


def main():
    load_dotenv(S.ROOT / ".env", override=False)
    key = os.environ.get("FIRMS_MAP_KEY", "").strip()
    if not key:
        raise ValueError("Falta FIRMS_MAP_KEY en el servidor.")
    S.INBOX.mkdir(parents=True, exist_ok=True)
    start, end = date(2001, 1, 1), date(2025, 12, 31)
    chunks = []
    registered = set(load_catalog()["items"])
    reported = set()
    client = httpx.Client(timeout=45)
    while start <= end:
        days = min(5, (end - start).days + 1)
        name = f"FIRMS_MODIS_SP_ayacucho-huanta_{start}_{days}.csv"
        if not (S.INBOX / name).exists() and name not in registered:
            chunks.append((start, days, name))
        start += timedelta(days=days)

    def fetch(item):
        stamp, days, name = item
        url = (f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/MODIS_SP/"
               f"-74.4,-13.4,-73.9,-12.8/{days}/{stamp}")
        for attempt in range(5):
            try:
                reserve(days)
                wait_for_remote_budget(key, client=client)
                response = client.get(url)
                if response.status_code != 200:
                    if response.status_code not in reported:
                        reported.add(response.status_code)
                        message = response.text.replace(key, "[redacted]")[:160]
                        print(f"FIRMS HTTP {response.status_code}: {message}", flush=True)
                    raise ValueError(f"NASA FIRMS respondió HTTP {response.status_code}.")
                body = response.text
                rows = csv.DictReader(io.StringIO(body))
                if not rows.fieldnames or not {"latitude", "longitude", "acq_date"} <= set(rows.fieldnames):
                    raise ValueError("NASA FIRMS no devolvió el CSV esperado.")
                if len(response.content) > 2_000_000:
                    raise ValueError("La ventana de cinco días supera 2 MB.")
                for row in rows:
                    observed = date.fromisoformat(row["acq_date"])
                    if not stamp <= observed < stamp + timedelta(days=days):
                        raise ValueError("FIRMS devolvió observaciones fuera del intervalo.")
                target = S.INBOX / name
                temporary = target.with_suffix(".partial")
                temporary.write_text(body, encoding="utf-8")
                temporary.replace(target)
                return
            except (httpx.HTTPError, ValueError) as error:
                if attempt == 4:
                    reason = str(error) if isinstance(error, ValueError) else type(error).__name__
                    raise RuntimeError(f"FIRMS del {stamp}: {reason}") from None
                time.sleep(2 ** (attempt + 1))

    print(f"FIRMS: {len(chunks)} ventanas pendientes; reserva persistente por intento", flush=True)
    try:
        for count, chunk in enumerate(chunks, 1):
            fetch(chunk)
            if count % 50 == 0:
                print(f"FIRMS: {count}/{len(chunks)} ventanas listas", flush=True)
    finally:
        client.close()
    print("FIRMS 2001–2025: originales listos para sarlab ingest.", flush=True)


if __name__ == "__main__":
    main()
