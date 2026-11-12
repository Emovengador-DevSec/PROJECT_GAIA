"""Recorre cualquier HDF5 y lista sus capas. Úsalo antes de configurar un producto nuevo."""
from __future__ import annotations

from pathlib import Path

import h5py


def inspect(path: str | Path, max_items: int = 400) -> list[str]:
    lines: list[str] = []
    with h5py.File(path, "r") as f:
        def visit(name, obj):
            if len(lines) >= max_items:
                return
            if isinstance(obj, h5py.Dataset):
                lines.append(f"{name}  shape={obj.shape}  dtype={obj.dtype}")
        f.visititems(visit)
    return lines
