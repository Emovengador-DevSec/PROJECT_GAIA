"""Prepara recortes locales de WorldPop y ESA WorldCover para la exposición en Ayacucho."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import rasterio
from rasterio.windows import from_bounds

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "02_interim" / "ayacucho-huanta"
BOUNDS = (-74.42, -13.42, -73.88, -12.78)
SOURCES = {
    "worldpop": {
        "date": "2025-01-01", "unit": "people_per_pixel",
        "url": ("https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2025/"
                "PER/v1/100m/constrained/per_pop_2025_CN_100m_R2025A_v1.tif"),
    },
    "worldcover": {
        "date": "2021-01-01", "unit": "class",
        "url": ("https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
                "ESA_WorldCover_10m_2021_v200_S15W075_Map.tif"),
    },
}


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=DEST) as staging, httpx.Client(timeout=40, follow_redirects=True) as client:
        for name, info in SOURCES.items():
            original = Path(staging) / f"{name}.tif"
            with client.stream("GET", info["url"]) as response, original.open("wb") as output:
                response.raise_for_status()
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > 100_000_000:
                        raise ValueError(f"El archivo {name} supera el tamaño esperado de 100 MB")
                    output.write(chunk)
            with rasterio.open(original) as source:
                if source.crs.to_epsg() != 4326:
                    raise ValueError(f"CRS inesperado de {name}: {source.crs}")
                window = from_bounds(*BOUNDS, transform=source.transform).round_offsets().round_lengths()
                data = source.read(1, window=window, masked=True)
                if not data.count():
                    raise ValueError(f"Sin datos de {name} en Ayacucho")
                profile = {"driver": "GTiff", "count": 1, "width": data.shape[1], "height": data.shape[0],
                           "dtype": source.dtypes[0], "crs": source.crs, "nodata": source.nodata,
                           "transform": source.window_transform(window), "compress": "deflate"}
                with rasterio.open(DEST / f"{name}.tif", "w", **profile) as target:
                    target.write(data.filled(), 1)
                    target.update_tags(source=info["url"], reference_date=info["date"], unit=info["unit"])
                print(f"{name} {info['date']}: {data.shape[1]} × {data.shape[0]}, "
                      f"{data.count()} píxeles válidos")
    metadata = {"retrieved_at": datetime.now(UTC).isoformat(), "bbox": BOUNDS, "sources": SOURCES}
    (DEST / "sources.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
