"""Lector de NISAR L2 GCOV (retrodispersión polarimétrica geocodificada).

Estructura verificada (ASF NISAR docs y Cookbook, nov. 2026):
  /science/LSAR/GCOV/grids/frequencyA/{HHHH,HVHV,mask,numberOfLooks,
                                       rtcGammaToSigmaFactor,xCoordinates,yCoordinates,projection}
  projection.attrs['epsg_code']  -> EPSG de la rejilla (UTM normalmente)
Las capas completas pesan GB: se lee SOLO la ventana de la zona (recorte por índices).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import h5py
import numpy as np

GRID = "/science/LSAR/GCOV/grids/{freq}"


def validate_sequence(paths: list[Path]) -> None:
    """Compare one GCOV geometry and one processing configuration across distinct dates."""
    geometries = set()
    dates = set()
    for path in paths:
        parts = Path(path).name.split("_")
        acquired = re.search(r"_(\d{8})T\d{6}_", Path(path).name)
        if (len(parts) < 12 or parts[:2] != ["NISAR", "L2"]
                or parts[3] != "GCOV" or not acquired):
            raise ValueError("Se requiere el nombre original de un producto NISAR L2 GCOV.")
        geometries.add(tuple(parts[5:11]))
        dates.add(acquired.group(1))
    if len(geometries) != 1:
        raise ValueError("Usa gránulos con la misma trayectoria, dirección, marco y polarizaciones.")
    if len(dates) != len(paths):
        raise ValueError("Cada observación debe corresponder a una fecha de adquisición distinta.")


@dataclass
class Window:
    data: np.ndarray            # valores lineales (potencia), float32
    x: np.ndarray               # centros de píxel (eje x, metros del EPSG)
    y: np.ndarray               # centros de píxel (eje y)
    epsg: int
    layer: str
    source: str
    mask: np.ndarray | None = None
    attrs: dict = field(default_factory=dict)

    @property
    def transform(self):
        from rasterio.transform import from_origin
        dx = float(self.x[1] - self.x[0]) if self.x.size > 1 else 1.0
        dy = float(self.y[0] - self.y[1]) if self.y.size > 1 else 1.0
        return from_origin(self.x[0] - dx / 2, self.y[0] + dy / 2, dx, abs(dy))


def list_layers(path: str | Path, freq: str = "frequencyA") -> list[str]:
    with h5py.File(path, "r") as f:
        return sorted(f[GRID.format(freq=freq)].keys())


def read_window(path: str | Path, layer: str, bbox_proj: tuple[float, float, float, float],
                freq: str = "frequencyA") -> Window:
    """Lee `layer` (p. ej. 'HHHH' o 'HVHV') dentro de una caja en coordenadas del producto."""
    xmin, ymin, xmax, ymax = bbox_proj
    with h5py.File(path, "r") as f:
        g = f[GRID.format(freq=freq)]
        if layer not in g:
            raise KeyError(f"La capa {layer} no existe. Disponibles: {sorted(g.keys())}")
        x = g["xCoordinates"][:]
        y = g["yCoordinates"][:]
        xi = np.where((x >= xmin) & (x <= xmax))[0]
        yi = np.where((y >= ymin) & (y <= ymax))[0]
        if xi.size == 0 or yi.size == 0:
            raise ValueError("La zona no intersecta la rejilla de este gránulo.")
        xs, ys = slice(xi.min(), xi.max() + 1), slice(yi.min(), yi.max() + 1)
        data = g[layer][ys, xs].astype("float32")
        mask = g["mask"][ys, xs] if "mask" in g else None
        if mask is not None:
            fill = int(np.asarray(g["mask"].attrs.get("_FillValue", 255)).item())
            data[(mask == 0) | (mask == fill)] = np.nan
        epsg = int(np.asarray(g["projection"].attrs.get("epsg_code")).item())
    return Window(data=data, x=x[xs], y=y[ys], epsg=epsg, layer=layer,
                  source=Path(path).name, mask=mask)


def bbox_to_product_crs(bbox_wgs84: tuple[float, float, float, float], epsg: int):
    """Convierte una caja lon/lat al sistema del producto."""
    from rasterio.warp import transform_bounds
    return transform_bounds("EPSG:4326", f"EPSG:{epsg}", *bbox_wgs84, densify_pts=21)


def study_area_mask(
    window: Window, bbox_wgs84: tuple[float, float, float, float],
) -> tuple[np.ndarray, float]:
    """Mask pixels outside the study polygon and return its projected area in m²."""
    from rasterio.features import geometry_mask
    from rasterio.warp import transform_geom
    from shapely.geometry import shape

    west, south, east, north = bbox_wgs84
    ring = [[west, south], [east, south], [east, north], [west, north], [west, south]]
    source = {"type": "Polygon", "coordinates": [ring]}
    projected = transform_geom("EPSG:4326", f"EPSG:{window.epsg}", source)
    mask = geometry_mask([projected], out_shape=window.data.shape, transform=window.transform, invert=True)
    return mask, shape(projected).area


def product_epsg(path: str | Path, freq: str = "frequencyA") -> int:
    with h5py.File(path, "r") as f:
        return int(np.asarray(f[GRID.format(freq=freq)]["projection"].attrs["epsg_code"]).item())
