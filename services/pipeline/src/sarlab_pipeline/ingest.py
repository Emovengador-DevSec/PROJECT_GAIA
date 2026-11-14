"""Ingesta: data/00_inbox -> validación -> data/01_raw (inmutable) + catálogo; fallos a cuarentena."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

import h5py

from . import settings as S

# Ej.: NISAR_L2_PR_GCOV_005_172_A_008_2005_DHDH_A_20251122T024618_20251122T024652_X05007_N_F_J_001.h5
NAME_RE = re.compile(r"^NISAR_(?P<level>L\d)_(?P<cfg>[A-Z]{2})_(?P<product>[A-Z0-9]{4})_.*?"
                     r"_(?P<start>\d{8}T\d{6})_(?P<end>\d{8}T\d{6})_.*\.h5$")
IMERG_RE = re.compile(r"^3B-DAY-L\.MS\.MRG\.3IMERG\.(?P<day>\d{8})"
                      r"-S000000-E235959\.V07B\.nc4$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def identify(path: Path) -> dict:
    imerg = IMERG_RE.fullmatch(path.name)
    if imerg:
        with h5py.File(path, "r"):
            pass  # Validate the NetCDF4 container before publishing the original.
        acquired = datetime.strptime(imerg["day"], "%Y%m%d").date().isoformat()
        return {"source": "gpm", "level": "L3", "cfg": "PR", "product": "IMERGDL",
                "start": imerg["day"] + "T000000", "end": imerg["day"] + "T235959",
                "acquired": acquired}
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
    if dest.exists():
        dest = S.QUARANTINE / f"{uuid4().hex}_{path.name}"
    shutil.move(str(path), dest)
    dest.with_name(f"{dest.name}.motivo.json").write_text(
        json.dumps({"motivo": reason, "fecha": datetime.now(UTC).isoformat()},
                   ensure_ascii=False, indent=2), encoding="utf-8")


def _catalog_path() -> Path:
    return S.CATALOG / "catalog.json"


def load_catalog() -> dict:
    p = _catalog_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"items": {}}


@contextmanager
def _ingest_lock():
    """Serialize catalogue updates without leaving a stale lock after a process crash."""
    with (S.CATALOG / ".ingest.lock").open("a+b") as lock:
        if lock.tell() == 0:
            lock.write(b"\0")
            lock.flush()
        lock.seek(0)
        if os.name == "nt":
            import msvcrt
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("Ya hay una ingesta en ejecución. Reintenta cuando termine.") from exc
        else:
            import fcntl
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("Ya hay una ingesta en ejecución. Reintenta cuando termine.") from exc
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _write_json(path: Path, value: dict) -> None:
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                            prefix=f".{path.stem}-", suffix=".tmp", delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, ensure_ascii=False, indent=2)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _publish_raw(source: Path, target: Path, digest: str) -> None:
    """Publish a complete, verified file atomically; an existing target is never replaced."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=target.parent, prefix=".ingest-", suffix=".partial", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        shutil.copyfile(source, temporary)
        if sha256(temporary) != digest:
            raise ValueError("El archivo de entrada cambió durante la copia. Vuelve a ingresarlo.")
        if os.name == "nt":
            # Windows rename raises FileExistsError instead of replacing an existing path.
            os.rename(temporary, target)
        else:
            os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def ingest_inbox() -> dict:
    S.CATALOG.mkdir(parents=True, exist_ok=True)
    with _ingest_lock():
        return _ingest_locked()


def _ingest_locked() -> dict:
    cat = load_catalog()
    checksums_p = S.CATALOG / "raw_checksums.json"
    checksums = json.loads(checksums_p.read_text()) if checksums_p.exists() else {}
    report = {"ingeridos": [], "omitidos": [], "cuarentena": [], "recuperados": []}
    accepted = []
    for path in sorted([*S.INBOX.glob("*.h5"), *S.INBOX.glob("*.nc4")]):
        if not path.is_file():
            continue
        try:
            if path.is_symlink():
                raise ValueError("La entrada debe ser un archivo independiente, no un enlace simbólico.")
            info = identify(path)
            digest = sha256(path)
            existing = cat["items"].get(path.name)
            expected = existing.get("sha256") if existing else None
            if expected is not None and digest != expected:
                raise ValueError("El nombre ya está registrado con otra suma SHA-256.")
            y, m = info["acquired"][:4], info["acquired"][5:7]
            rel = Path(existing["path"]) if existing else (
                Path(info.get("source", "nisar")) / info["product"].lower() / y / m / path.name)
            dest = (S.RAW / rel).resolve()
            if not dest.is_relative_to(S.RAW.resolve()):
                raise ValueError("La ruta registrada sale de data/01_raw.")
            present = dest.exists()
            if present and sha256(dest) != digest:
                raise ValueError("Existe otro contenido en 01_raw. Se conserva para revisión manual.")
            if not present:
                _publish_raw(path, dest, digest)
        except Exception as exc:  # noqa: BLE001
            _quarantine(path, str(exc)); report["cuarentena"].append(path.name); continue
        cat["items"][path.name] = {**info, **(existing or {}), "path": str(rel), "sha256": digest,
                                   "ingested_at": (existing or {}).get("ingested_at")
                                   or datetime.now(UTC).isoformat(timespec="seconds"),
                                   "quality_flags": (existing or {}).get("quality_flags",
                                       ["provisional"] if info["cfg"] == "PR" else [])}
        checksums[str(rel)] = digest
        if existing and present:
            report["omitidos"].append(path.name)
        elif existing or present:
            report["recuperados"].append(path.name)
        else:
            report["ingeridos"].append(path.name)
        accepted.append(path)
    _write_json(_catalog_path(), cat)
    _write_json(checksums_p, checksums)
    for path in accepted:
        path.unlink()
    return report
