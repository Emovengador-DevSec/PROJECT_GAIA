"""Rutas y variables de entorno. Nada de secretos en el código."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ.get("SARLAB_ROOT", Path(__file__).resolve().parents[4]))
CONFIG_DIR = ROOT / "config"
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data")).resolve()

INBOX = DATA_DIR / "00_inbox"
RAW = DATA_DIR / "01_raw"
INTERIM = DATA_DIR / "02_interim"
PROCESSED = DATA_DIR / "03_processed"
PUBLISHED = DATA_DIR / "04_published"
QUARANTINE = DATA_DIR / "99_quarantine"
CATALOG = DATA_DIR / "catalog"


def earthdata_token() -> str | None:
    """Token de Earthdata Login (solo servidor). Devuelve None si no está definido."""
    return os.environ.get("EARTHDATA_TOKEN") or None
