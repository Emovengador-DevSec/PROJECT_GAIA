"""Physical slope and conservation of exposed cropland, using isolated synthetic rasters."""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform_geom
from shapely.geometry import box, mapping

from sarlab_pipeline.agriculture import FIELDS, slope_degrees, slope_exposure


def test_slope_of_plane_and_missing_edges():
    plane = np.tile(np.arange(5, dtype="float32") * 10, (5, 1))
    result = slope_degrees(plane, 30)
    assert result[2, 2] == pytest.approx(np.degrees(np.arctan(1 / 3)), abs=1e-5)
    assert np.isnan(result[0]).all() and np.isnan(result[:, -1]).all()


def test_cropland_classes_conserve_area_and_keep_unknown(tmp_path):
    cover, slope = tmp_path / "cover.tif", tmp_path / "slope.tif"
    profile = {"driver": "GTiff", "width": 3, "height": 1, "count": 1,
               "crs": "EPSG:32718", "transform": from_origin(500000, 8600000, 10, 10)}
    with rasterio.open(cover, "w", **profile, dtype="uint8", nodata=0) as raster:
        raster.write(np.array([[40, 40, 40]], "uint8"), 1)
    with rasterio.open(slope, "w", **profile, dtype="float32", nodata=np.nan) as raster:
        raster.write(np.array([[15, 20, np.nan]], "float32"), 1)
    geometry = transform_geom("EPSG:32718", "EPSG:4326", mapping(box(500000, 8599990, 500030, 8600000)))
    result = slope_exposure(geometry, cover, slope, .03)
    assert all(result[key] == .01 for key in FIELDS)
    assert sum(result.values()) == pytest.approx(.03)
