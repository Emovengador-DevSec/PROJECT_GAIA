"""Carga y valida la configuración de config/ con Pydantic."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from .settings import CONFIG_DIR


class AOI(BaseModel):
    id: str
    name: str
    role: Literal["flagship", "support", "optional"]
    status: Literal["approximate", "confirmed"]
    bbox: tuple[float, float, float, float] = Field(description="oeste, sur, este, norte (EPSG:4326)")
    phenomena: list[str]
    notes: str | None = None
    camera: dict | None = None

    @field_validator("bbox")
    @classmethod
    def _bbox_ok(cls, v):
        w, s, e, n = v
        if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
            raise ValueError("bbox debe ser [oeste, sur, este, norte] dentro de rango")
        return v

    def wkt(self) -> str:
        w, s, e, n = self.bbox
        return f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"


class Thresholds(BaseModel):
    coherence_min: float = 0.3
    change_k_sigma: float = 3.0
    min_alert_pixels: int = 25


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_aois(config_dir: Path = CONFIG_DIR) -> dict[str, AOI]:
    aois = {}
    for p in sorted((config_dir / "aois").glob("*.yaml")):
        aoi = AOI(**_load(p))
        if aoi.id != p.stem:
            raise ValueError(f"{p.name}: id '{aoi.id}' no coincide con el nombre del archivo")
        aois[aoi.id] = aoi
    return aois


def load_thresholds(config_dir: Path = CONFIG_DIR) -> Thresholds:
    raw = _load(config_dir / "thresholds.yaml")
    return Thresholds(
        coherence_min=raw.get("coherence_min", {}).get("value", 0.3),
        change_k_sigma=raw.get("backscatter_change", {}).get("k_sigma", 3.0),
        min_alert_pixels=raw.get("min_alert_pixels", {}).get("value", 25),
    )


def load_product(product_id: str, config_dir: Path = CONFIG_DIR) -> dict:
    return _load(config_dir / "products" / f"{product_id}.yaml")
