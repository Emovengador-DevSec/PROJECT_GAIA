import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform_geom

from sarlab_pipeline import exposure
from sarlab_pipeline import settings as S


def _alert(monkeypatch):
    monkeypatch.setattr(exposure, "load_aois", lambda: {"test": object()})
    geom = {"type": "Polygon", "coordinates": [[[360000, 8600000], [360200, 8600000],
            [360200, 8599800], [360000, 8599800], [360000, 8600000]]]}
    geom = transform_geom(32719, 4326, geom)
    output = S.PROCESSED / "test" / "gcov" / "period"
    output.mkdir(parents=True)
    (output / "alerts_hvhv.geojson").write_text(json.dumps({"type": "FeatureCollection", "crs_epsg": 4326,
        "features": [{"type": "Feature", "geometry": geom, "properties": {"id": "alert-test"}}]}))
    return geom


def _raster(path, values):
    with rasterio.open(path, "w", driver="GTiff", height=2, width=2, count=1, dtype="float32",
                       crs="EPSG:32719", transform=from_origin(360000, 8600000, 100, 100),
                       nodata=-9999) as dst:
        dst.write(np.asarray(values, dtype="float32"), 1)
    return path


def test_exposure_uses_real_cell_units_and_places(data_dirs, tmp_path, monkeypatch):
    geom = _alert(monkeypatch)
    pop = _raster(tmp_path / "population.tif", [[1, 2], [3, 4]])
    cover = _raster(tmp_path / "landcover.tif", [[40, 40], [10, 20]])
    inside = geom["coordinates"][0][0]
    places = tmp_path / "places.geojson"
    places.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": inside},
         "properties": {"name": "Test village"}},
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-75, -15]},
         "properties": {"name": "Far village"}},
    ]}))
    result = exposure.calculate("test", pop, cover, places, "people_per_pixel",
                                "2025-01-01", "2021-01-01", "2026-11-13")
    row = result["alerts"]["alert-test"]
    assert row["population"] == 10
    assert row["cropland_ha"] == 2
    assert row["forest_ha"] == 1
    assert row["settlements"] == 1
    assert row["sources"]["population"]["unit"] == "people_per_pixel"
    assert (S.PUBLISHED / "exposure" / "test.json").exists()


def test_missing_exposure_sources_are_null(data_dirs, monkeypatch):
    _alert(monkeypatch)
    row = exposure.calculate("test")["alerts"]["alert-test"]
    assert row["population"] is None and row["cropland_ha"] is None and row["settlements"] is None
    assert len(row["issues"]) == 3


def test_population_density_requires_explicit_conversion(data_dirs, tmp_path, monkeypatch):
    _alert(monkeypatch)
    with pytest.raises(ValueError, match="people_per_pixel"):
        exposure.calculate("test", population=tmp_path / "density.tif")
