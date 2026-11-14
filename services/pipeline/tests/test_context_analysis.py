"""Casos sintéticos de máscaras, fechas y unidades para los cruces de fuentes."""

import json
from datetime import date

import numpy as np
import pytest
import rasterio
import xarray as xr
from rasterio.transform import from_origin
from rasterio.warp import transform_geom

from sarlab_pipeline import settings
from sarlab_pipeline.processing.rainfall import three_day_rain
from sarlab_pipeline.processing.validation import compare_opera


def test_opera_uses_confirmed_changes_in_common_coverage(data_dirs):
    folder = settings.PROCESSED / "test" / "gcov" / "pair"
    folder.mkdir(parents=True)
    raster = folder / "diff_hvhv_db.tif"
    transform = from_origin(360000, 8600000, 100, 100)
    profile = dict(driver="GTiff", height=2, width=3, count=1, crs="EPSG:32719", transform=transform)
    with rasterio.open(raster, "w", **profile, dtype="float32", nodata=np.nan) as dst:
        dst.write(np.array([[0, 0, 0], [np.nan, 0, 0]], "float32"), 1)
    manifest = {"id": "test", "cog_path": str(raster), "provenance": {"product": "GCOV"},
                "dates": {"a": "2026-06-19", "b": "2026-10-05"}}
    (folder / "manifest_hvhv.json").write_text(json.dumps(manifest))
    geometry = transform_geom("EPSG:32719", "EPSG:4326", {
        "type": "Polygon", "coordinates": [[[360000, 8600000], [360200, 8600000],
                                            [360200, 8599900], [360000, 8599900], [360000, 8600000]]],
    })
    alerts = folder / "alerts_hvhv.geojson"
    alerts.write_text(json.dumps({"features": [{"geometry": geometry, "properties": {"layer_id": "test"}}]}))
    name = "OPERA_L3_DIST-ALERT-HLS_T19LCG_20261008T150721Z_20261010T061317Z_S2C_30_v1"
    status = settings.INTERIM / f"{name}_VEG-DIST-STATUS.tif"
    onset = settings.INTERIM / f"{name}_VEG-DIST-DATE.tif"
    with rasterio.open(status, "w", **profile, dtype="uint8", nodata=255) as dst:
        dst.write(np.array([[3, 2, 6], [0, 255, 3]], "uint8"), 1)
    day = (date(2026, 7, 1) - date(2020, 12, 31)).days
    with rasterio.open(onset, "w", **profile, dtype="int16", nodata=-1) as dst:
        dst.write(np.array([[day, day, 1], [0, -1, day + 200]], "int16"), 1)
    result = compare_opera("test", status, onset, name, "2026-10-08")
    assert result["common_ha"] == 4
    assert result["nisar_loss_ha"] == 2
    assert result["opera_disturbance_ha"] == 1
    assert result["overlap_ha"] == 1
    assert result["agreement_pct"] == 50
    assert result["nisar_confirmed_pct"] == 50
    with pytest.raises(ValueError, match="fecha OPERA"):
        compare_opera("test", status, onset, name, "2026-10-10")
    alerts.write_text(json.dumps({"features": []}))
    assert compare_opera("test", status, onset, name, "2026-10-08")["nisar_loss_ha"] == 0
    companion = "OPERA_L3_DIST-ALERT-HLS_T19LCH_20261008T150721Z_20261010T061317Z_S2C_30_v1"
    extra_status = settings.INTERIM / f"{companion}_VEG-DIST-STATUS.tif"
    extra_onset = settings.INTERIM / f"{companion}_VEG-DIST-DATE.tif"
    with rasterio.open(extra_status, "w", **profile, dtype="uint8", nodata=255) as dst:
        dst.write(np.array([[255, 255, 255], [255, 3, 255]], "uint8"), 1)
    with rasterio.open(extra_onset, "w", **profile, dtype="int16", nodata=-1) as dst:
        dst.write(np.array([[-1, -1, -1], [-1, day, -1]], "int16"), 1)
    combined = compare_opera("test", status, onset, name, "2026-10-08",
                             [(extra_status, extra_onset, companion, "2026-10-08")])
    assert combined["common_ha"] == 5
    assert combined["opera_disturbance_ha"] == 2
    assert len(combined["granules"]) == 2


def test_imerg_three_days_require_common_data_and_consecutive_dates(data_dirs):
    paths = []
    for index, day in enumerate(("2026-02-22", "2026-02-23", "2026-02-24")):
        values = np.array([[[1, 2], [3, 4]]], dtype="float32") * (index + 1)
        if index == 2:
            values[0, 0, 0] = np.nan
        ds = xr.Dataset(
            {"precipitation": (("time", "lat", "lon"), values, {"units": "mm/day"})},
            coords={"time": [np.datetime64(day)], "lat": [-12.0, -11.9], "lon": [-76.8, -76.6]},
        )
        for key, role in (("time", "time"), ("lat", "latitude"), ("lon", "longitude")):
            ds[key].attrs["standard_name"] = role
        path = settings.INTERIM / f"3B-DAY-E.MS.MRG.3IMERG.{day.replace('-', '')}.V07B.nc4"
        ds.to_netcdf(path, engine="h5netcdf")
        paths.append(path)
    result = three_day_rain("chosica-rimac", paths, "precipitation")
    assert result["valid_area_pct"] == 75
    assert result["dates"] == ["2026-02-22", "2026-02-23", "2026-02-24"]
    assert 17.9 < result["mean_mm"] < 18.1
    with pytest.raises(ValueError, match="consecutivos"):
        three_day_rain("chosica-rimac", [paths[0], paths[0], paths[2]], "precipitation")
    with pytest.raises(ValueError, match="Confirma la variable"):
        three_day_rain("chosica-rimac", paths, "wrong")
