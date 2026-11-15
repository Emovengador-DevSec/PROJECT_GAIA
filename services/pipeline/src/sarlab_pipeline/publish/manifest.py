"""Manifiesto de capa: procedencia + calidad viajan con cada resultado."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from .. import settings
from .paths import relative_cog


def build(layer_id: str, kind: str, title: str, unit: str, colormap: str, arr: np.ndarray,
          cog_path: Path, aoi_id: str, dates: dict, granules: list[str], extra: dict | None = None,
          provisional: bool = True) -> dict:
    v = arr[np.isfinite(arr)]
    return {
        "id": layer_id, "kind": kind, "title": title, "unit": unit, "colormap": colormap,
        "range": {"min": float(np.percentile(v, 2)) if v.size else None,
                  "max": float(np.percentile(v, 98)) if v.size else None},
        "cog_path": relative_cog(cog_path, settings.PROCESSED), "aoi_id": aoi_id, "dates": dates,
        "provenance": {"source": "NISAR", "granules": granules,
                       "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                       **(extra or {})},
        "quality": {"provisional": provisional,
                    "valid_area_pct": round(100 * float(np.isfinite(arr).mean()), 2) if arr.size else 0.0},
    }


def write(manifest: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def fix_manifests() -> dict:
    from ..field_evidence import write_json

    pending = []
    for path in sorted(settings.PROCESSED.glob("*/*/*/manifest*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for section in (document, document.get("comparison") or {}):
            for key in ("cog_path", "before_cog_path", "after_cog_path"):
                if key in section:
                    relative = relative_cog(section[key], settings.PROCESSED)
                    changed |= relative != section[key]
                    section[key] = relative
        if changed:
            pending.append((path, document))
    for path, document in pending:
        write_json(path, document)
    return {"updated": len(pending)}
