"""Fixtures SINTÉTICOS solo para pruebas unitarias. Nunca llegan a la interfaz."""
from __future__ import annotations

import h5py
import numpy as np
import pytest

GRID = "/science/LSAR/GCOV/grids/frequencyA"


def make_synthetic_gcov(path, hv_scale=1.0, clearing=False, seed=0, epsg=32719):
    """Imita la estructura documentada del GCOV (rejilla UTM 19S cerca de Madre de Dios)."""
    rng = np.random.default_rng(seed)
    ny, nx, step = 120, 140, 100.0
    x0, y0 = 360000.0, 8600000.0        # UTM 19S aprox. (~ -70.3, -12.6)
    x = x0 + step * np.arange(nx)
    y = y0 - step * np.arange(ny)
    hv = (0.05 * hv_scale * rng.gamma(4, 0.25, (ny, nx))).astype("float32")
    if clearing:
        hv[40:70, 50:90] *= 0.15        # "deforestación" sintética: caída de HV
    with h5py.File(path, "w") as f:
        g = f.create_group(GRID)
        g["HVHV"] = hv
        g["HHHH"] = (hv * 4).astype("float32")
        g["mask"] = np.ones((ny, nx), "uint8")
        g["xCoordinates"] = x
        g["yCoordinates"] = y
        p = g.create_dataset("projection", data=np.int32(epsg))
        p.attrs["epsg_code"] = np.int32(epsg)
    return path


@pytest.fixture()
def data_dirs(tmp_path, monkeypatch):
    from sarlab_pipeline import settings as S
    for name in ("INBOX", "RAW", "INTERIM", "PROCESSED", "PUBLISHED", "QUARANTINE", "CATALOG"):
        d = tmp_path / name.lower(); d.mkdir()
        monkeypatch.setattr(S, name, d)
    return tmp_path
