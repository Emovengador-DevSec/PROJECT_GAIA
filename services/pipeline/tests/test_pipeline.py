import json
from pathlib import Path

import numpy as np
import pytest

from conftest import make_synthetic_gcov
from sarlab_pipeline.detection.change import robust_threshold
from sarlab_pipeline.processing.backscatter import boxcar, to_db
from sarlab_pipeline.readers import gcov

NAME = "NISAR_L2_PR_GCOV_005_172_A_008_2005_DHDH_A_{d}T024618_{d}T024652_X05007_N_F_J_001.h5"


def test_to_db_basics():
    out = to_db(np.array([1.0, 0.1, 0.0, np.nan], dtype="float32"))
    assert out[0] == pytest.approx(0.0) and out[1] == pytest.approx(-10.0)
    assert np.isnan(out[2]) and np.isnan(out[3])


def test_boxcar_keeps_shape_and_ignores_nan():
    a = np.ones((5, 5), "float32"); a[2, 2] = np.nan
    b = boxcar(a, 3)
    assert b.shape == a.shape and np.nanmax(np.abs(b - 1)) < 1e-6


def test_robust_threshold_flags_loss():
    rng = np.random.default_rng(1)
    d = rng.normal(0, 0.5, (100, 100)).astype("float32")
    d[10:20, 10:20] = -8
    r = robust_threshold(d, 3)
    assert r.loss[10:20, 10:20].all() and r.loss.sum() < 300


def test_read_window_subsets_by_bbox(tmp_path):
    p = make_synthetic_gcov(tmp_path / NAME.format(d="20251122"))
    assert "HVHV" in gcov.list_layers(p)
    w = gcov.read_window(p, "HVHV", (361000, 8592000, 365000, 8597000))
    assert w.epsg == 32719 and w.data.shape == (51, 41)


def test_read_window_outside_raises(tmp_path):
    p = make_synthetic_gcov(tmp_path / NAME.format(d="20251122"))
    with pytest.raises(ValueError):
        gcov.read_window(p, "HVHV", (0, 0, 10, 10))


def test_gcov_reader_excludes_unfocused_and_fill_pixels_with_finite_power(tmp_path):
    import h5py

    path = make_synthetic_gcov(tmp_path / NAME.format(d="20251122"))
    with h5py.File(path, "r+") as file:
        mask = file[gcov.GRID.format(freq="frequencyA")]["mask"]
        mask[0, :3] = [0, 255, 1]
    window = gcov.read_window(path, "HVHV", (360000, 8600000, 360200, 8600000))
    assert np.isnan(window.data[0, :2]).all()
    assert np.isfinite(window.data[0, 2])


def test_ingest_moves_and_quarantines(data_dirs):
    from sarlab_pipeline import settings as S
    from sarlab_pipeline.ingest import ingest_inbox
    make_synthetic_gcov(S.INBOX / NAME.format(d="20251122"))
    (S.INBOX / "basura.h5").write_bytes(b"no soy hdf5")
    rep = ingest_inbox()
    assert len(rep["ingeridos"]) == 1 and rep["cuarentena"] == ["basura.h5"]
    assert (S.QUARANTINE / "basura.h5.motivo.json").exists()
    cat = json.loads((S.CATALOG / "catalog.json").read_text())
    item = next(iter(cat["items"].values()))
    assert item["product"] == "GCOV" and item["acquired"] == "2025-11-22"
    assert "provisional" in item["quality_flags"]


def test_ingest_imerg_preserves_original_and_checksums(data_dirs):
    import h5py

    from sarlab_pipeline import settings as S
    from sarlab_pipeline.ingest import ingest_inbox, sha256

    name = "3B-DAY-L.MS.MRG.3IMERG.20260222-S000000-E235959.V07B.nc4"
    with h5py.File(S.INBOX / name, "w") as file:
        file.attrs["test_fixture"] = True
    digest = sha256(S.INBOX / name)
    assert ingest_inbox()["ingeridos"] == [name]
    catalog = json.loads((S.CATALOG / "catalog.json").read_text())
    item = catalog["items"][name]
    assert item["source"] == "gpm" and item["acquired"] == "2026-02-22"
    assert sha256(S.RAW / item["path"]) == digest
    assert not (S.INBOX / name).exists()


def test_change_workflow_end_to_end(data_dirs, tmp_path, monkeypatch):
    from sarlab_pipeline import workflows
    from sarlab_pipeline.config import AOI, Thresholds  # noqa: F401
    a = make_synthetic_gcov(tmp_path / NAME.format(d="20251122"), seed=1)
    b = make_synthetic_gcov(tmp_path / NAME.format(d="20260310"), seed=2, clearing=True)
    # Zona de prueba: caja lon/lat que cae dentro de la rejilla sintética
    aoi = AOI(id="test", name="t", role="flagship", status="approximate",
              bbox=(-70.29, -12.70, -70.18, -12.62), phenomena=["deforestation"])
    monkeypatch.setattr(workflows, "load_aois", lambda: {"test": aoi})
    monkeypatch.setattr(workflows, "load_thresholds", lambda: Thresholds(min_alert_pixels=20))
    r = workflows.change_between("test", a, b, "HVHV")
    assert r["alerts"] >= 1 and r["loss_area_ha"] > 0
    man = r["manifest"]
    assert man["dates"] == {"a": "2025-11-22", "b": "2026-03-10"}
    assert man["quality"]["provisional"] is True
    assert man["change_summary"]["loss_area_ha"] == r["loss_area_ha"]
    assert man["change_summary"]["alerts"] == r["alerts"]
    import rasterio
    with rasterio.open(man["cog_path"]) as src:
        assert src.crs.to_epsg() == 32719 and src.count == 1
    assert man["comparison"]["range"]["min"] < man["comparison"]["range"]["max"]
    assert Path(man["comparison"]["before_cog_path"]).exists()
    collection = json.loads((Path(r["out_dir"]) / "alerts_hvhv.geojson").read_text())
    assert collection["crs_epsg"] == 4326
    for feature in collection["features"]:
        assert feature["properties"]["area_ha"] > 0
        assert feature["properties"]["loss_pixels"] >= 20
        assert feature["properties"]["source"] == "NISAR"
        assert feature["properties"]["provisional"] is True
        for ring in feature["geometry"]["coordinates"]:
            assert all(-180 <= x <= 180 and -90 <= y <= 90 for x, y in ring)


def _aoi_patch(monkeypatch, *modules):
    from sarlab_pipeline.config import AOI, Thresholds
    aoi = AOI(id="test", name="t", role="flagship", status="approximate",
              bbox=(-70.29, -12.70, -70.18, -12.62), phenomena=["deforestation"])
    for m in modules:
        monkeypatch.setattr(m, "load_aois", lambda: {"test": aoi})
        if hasattr(m, "load_thresholds"):
            monkeypatch.setattr(m, "load_thresholds", lambda: Thresholds(min_alert_pixels=20))


def test_change_multi_compares_polarizations(data_dirs, tmp_path, monkeypatch):
    from sarlab_pipeline import workflows
    _aoi_patch(monkeypatch, workflows)
    a = make_synthetic_gcov(tmp_path / NAME.format(d="20251122"), seed=1)
    b = make_synthetic_gcov(tmp_path / NAME.format(d="20260310"), seed=2, clearing=True)
    r = workflows.change_multi("test", a, b)
    assert set(r["by_layer"]) == {"HHHH", "HVHV"}
    assert r["summary"]["strongest"] in {"HHHH", "HVHV"}


def test_false_color_tiles_keep_granules_and_masks_aligned(data_dirs, tmp_path, monkeypatch):
    from fastapi import HTTPException
    from rasterio.io import MemoryFile

    from app import main
    from sarlab_pipeline import settings, workflows
    from sarlab_pipeline.processing.false_color import backscatter_rgb

    rgb, mask = backscatter_rgb(np.array([[-15.0, np.nan]]), np.array([[-20.0, -20.0]]))
    assert rgb[:, 0, 0].tolist() == [128, 128, 85]
    assert mask.tolist() == [[255, 0]]

    _aoi_patch(monkeypatch, workflows)
    monkeypatch.setattr(main, "PROCESSED", settings.PROCESSED)
    a = make_synthetic_gcov(tmp_path / NAME.format(d="20251122"), seed=1)
    b = make_synthetic_gcov(tmp_path / NAME.format(d="20260310"), seed=2, clearing=True)
    workflows.change_multi("test", a, b)
    manifest = next(item for item in main.layers("test") if item["provenance"]["layer"] == "HHHH")
    for stage in ("before", "after"):
        png = main.tile(manifest["id"], stage, 10, 312, 548, palette="rgb")
        with MemoryFile(png.body) as file, file.open() as image:
            assert image.count == 4
            alpha = image.read(4)
            assert alpha.max() == 255 and alpha.min() == 0

    other_path = next(settings.PROCESSED.rglob("manifest_hvhv.json"))
    other = json.loads(other_path.read_text(encoding="utf-8"))
    other["provenance"]["granules"][0] = "other-granule"
    other_path.write_text(json.dumps(other), encoding="utf-8")
    with pytest.raises(HTTPException, match="mismas dos observaciones") as error:
        main.tile(manifest["id"], "before", 10, 312, 548, palette="rgb")
    assert error.value.status_code == 404


def test_timeseries_orders_dates_and_ratio(data_dirs, tmp_path, monkeypatch):
    from sarlab_pipeline import analysis
    _aoi_patch(monkeypatch, analysis)
    files = [make_synthetic_gcov(tmp_path / NAME.format(d=d), seed=i, clearing=i == 2)
             for i, d in enumerate(["20260310", "20251122", "20260104"])]
    r = analysis.timeseries("test", files)
    dates = [s["date"] for s in r["samples"]]
    assert dates == sorted(dates) and len(dates) == 3
    assert r["samples"][0]["HVHV"]["median_db"] < 0
    assert r["samples"][0]["HV_HH_ratio_db"] == pytest.approx(-6.02, abs=0.1)  # HH = 4*HV


def test_active_comparison_keeps_archived_periods_available(data_dirs, monkeypatch):
    from fastapi.testclient import TestClient

    from app import main
    from sarlab_pipeline import settings

    monkeypatch.setattr(main, "PROCESSED", settings.PROCESSED)
    base = settings.PROCESSED / "test" / "gcov"
    old, new = "2026-06-19__2026-10-05", "2026-06-24__2026-10-10"
    for period in (old, new):
        folder = base / period
        folder.mkdir(parents=True)
        first, last = period.split("__")
        manifest = {"id": period, "aoi_id": "test", "dates": {"a": first, "b": last},
                    "provenance": {"product": "GCOV", "layer": "HVHV"},
                    "change_summary": {"loss_area_ha": 20, "mapped_loss_area_ha": 15, "alerts": 1}}
        (folder / "manifest_hvhv.json").write_text(json.dumps(manifest))
        (folder / "alerts_hvhv.geojson").write_text(json.dumps({"features": [{"type": "Feature",
            "geometry": None,
            "properties": {"id": period, "layer_id": period, "date_range": [first, last]}}]}))
        (folder / "timeseries.json").write_text(json.dumps({"period": period, "samples": []}))
        (folder / "polarizations.json").write_text(json.dumps({"period": period}))
    (base / "active-comparison.json").write_text(json.dumps({"period": new}))
    client = TestClient(main.app)
    assert len(client.get("/api/layers?aoi=test").json()) == 2
    assert client.get("/api/layers?aoi=test&active_only=true").json()[0]["id"] == new
    assert client.get(f"/api/layers/{old}").status_code == 200
    alerts = client.get("/api/alerts?aoi=test&active_only=true").json()["features"]
    assert [item["properties"]["id"] for item in alerts] == [new]
    assert alerts[0]["properties"]["comparison_summary"]["loss_area_ha"] == 20
    assert client.get("/api/timeseries?aoi=test").json()["period"] == new
    assert client.get("/api/polarizations?aoi=test&active_only=true").json() == [{"period": new}]
    exposure = main.PROCESSED.parent / "04_published" / "exposure" / "test.json"
    exposure.parent.mkdir(parents=True)
    exposure.write_text(json.dumps({"alerts": {}}))
    read_text = Path.read_text
    reads = []

    def tracked_read(path, *args, **kwargs):
        if path == exposure:
            reads.append(path)
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", tracked_read)
    assert len(client.get("/api/alerts?aoi=test").json()["features"]) == 1
    assert len(reads) == 1
    assert len(client.get("/api/alerts?aoi=test&active_only=false").json()["features"]) == 2
