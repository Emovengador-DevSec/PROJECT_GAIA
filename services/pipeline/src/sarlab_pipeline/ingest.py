"""Ingesta: data/00_inbox -> validación -> data/01_raw (inmutable) + catálogo; fallos a cuarentena."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

import h5py

from . import settings as S

# Ej.: NISAR_L2_PR_GCOV_005_172_A_008_2005_DHDH_A_20251122T024618_20251122T024652_X05007_N_F_J_001.h5
NAME_RE = re.compile(r"^NISAR_(?P<level>L\d)_(?P<cfg>[A-Z]{2})_(?P<product>[A-Z0-9]{4})_.*?"
                     r"_(?P<start>\d{8}T\d{6})_(?P<end>\d{8}T\d{6})_.*\.h5$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def identify(path: Path) -> dict:
    m = NAME_RE.match(path.name)
    if not m:
        raise ValueError("nombre no reconocido como producto NISAR")
    info = m.groupdict()
    with h5py.File(path, "r") as f:   # comprueba que se puede abrir
        if f"/science/LSAR/{info['product']}" not in f:
            raise ValueError(f"no contiene el grupo /science/LSAR/{info['product']}")
    info["acquired"] = datetime.strptime(info["start"], "%Y%m%dT%H%M%S").date().isoformat()
    return info


def _quarantine(path: Path, reason: str) -> None:
    S.QUARANTINE.mkdir(parents=True, exist_ok=True)
    dest = S.QUARANTINE / path.name
    shutil.move(str(path), dest)
    (S.QUARANTINE / f"{path.name}.motivo.json").write_text(
        json.dumps({"motivo": reason, "fecha": datetime.now(UTC).isoformat()},
                   ensure_ascii=False, indent=2), encoding="utf-8")


def _catalog_path() -> Path:
    return S.CATALOG / "catalog.json"


def load_catalog() -> dict:
    p = _catalog_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"items": {}}


def ingest_inbox() -> dict:
    S.CATALOG.mkdir(parents=True, exist_ok=True)
    cat = load_catalog()
    checksums_p = S.CATALOG / "raw_checksums.json"
    checksums = json.loads(checksums_p.read_text()) if checksums_p.exists() else {}
    report = {"ingeridos": [], "omitidos": [], "cuarentena": []}
    for path in sorted(S.INBOX.glob("*.h5")):
        try:
            info = identify(path)
        except Exception as exc:  # noqa: BLE001
            _quarantine(path, str(exc)); report["cuarentena"].append(path.name); continue
        digest = sha256(path)
        if path.name in cat["items"]:
            path.unlink(); report["omitidos"].append(path.name); continue
        y, m = info["acquired"][:4], info["acquired"][5:7]
        rel = Path("nisar") / info["product"].lower() / y / m / path.name
        dest = S.RAW / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), dest)
        cat["items"][path.name] = {**info, "path": str(rel), "sha256": digest,
                                   "ingested_at": datetime.now(UTC).isoformat(timespec="seconds"),
                                   "quality_flags": ["provisional"] if info["cfg"] == "PR" else []}
        checksums[str(rel)] = digest
        report["ingeridos"].append(path.name)
    _catalog_path().write_text(json.dumps(cat, ensure_ascii=False, indent=2), encoding="utf-8")
    checksums_p.write_text(json.dumps(checksums, indent=2), encoding="utf-8")
    return report
