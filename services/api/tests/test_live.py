import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app import live
from app.main import app


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "CACHE", tmp_path)
    monkeypatch.setattr(live, "FAILURES", {})
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)


def test_missing_firms_key_is_explicit():
    response = TestClient(app).get("/api/live/fires")
    assert response.status_code == 200
    payload = response.json()
    assert payload["features"] == []
    assert payload["last_updated"] is None
    assert "FIRMS_MAP_KEY" in payload["message"]


def test_cache_rejects_naive_and_future_dates(tmp_path):
    path = tmp_path / "quakes.json"
    for stamp in ("2026-11-13T00:00:00", (datetime.now(UTC) + timedelta(days=1)).isoformat()):
        path.write_text(json.dumps({"type": "FeatureCollection", "features": [], "last_updated": stamp}))
        assert live._read(path) is None


def test_error_uses_last_observation_and_cooldown(tmp_path, monkeypatch):
    stamp = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    live._save(
        tmp_path / "quakes.json",
        {
            "type": "FeatureCollection",
            "features": [],
            "source": "USGS",
            "status": "ok",
            "last_updated": stamp,
        },
    )
    calls = []

    def fail():
        calls.append(True)
        raise httpx.ConnectError("Network unavailable")

    monkeypatch.setattr(live, "_quakes", fail)
    first = live.collection("quakes")
    second = live.collection("quakes")
    assert first["stale"] and second["stale"]
    assert first["last_updated"] == stamp
    assert len(calls) == 1


def test_upstream_exception_does_not_disclose_key(monkeypatch):
    marker = "test-key-never-public"
    monkeypatch.setenv("FIRMS_MAP_KEY", marker)

    def fail(_key):
        raise httpx.ConnectError("https://example.invalid/" + marker)

    monkeypatch.setattr(live, "_fires", fail)
    payload = live.collection("fires")
    assert marker not in json.dumps(payload)
    assert payload["status"] == "unavailable"


def test_tiles_reject_client_paths_and_invalid_coordinates():
    client = TestClient(app)
    assert client.get("/api/tiles/no-layer/change/20/0/0.png").status_code == 422
    assert client.get("/api/tiles/no-layer/other/1/0/0.png").status_code == 422
    assert client.get("/api/tiles/no-layer/change/1/0/0.png").status_code == 404
    assert client.get("/api/catalog?aoi=../../etc").status_code == 422


def test_published_comparison_serves_real_png(tmp_path, monkeypatch):
    from rasterio.io import MemoryFile

    from app import main
    from conftest import make_synthetic_gcov
    from sarlab_pipeline import settings, workflows
    from sarlab_pipeline.config import AOI, Thresholds

    pattern = "NISAR_L2_PR_GCOV_005_172_A_008_2005_DHDH_A_{d}T024618_{d}T024652_X05007_N_F_J_001.h5"
    before = make_synthetic_gcov(tmp_path / pattern.format(d="20251122"), seed=1)
    after = make_synthetic_gcov(tmp_path / pattern.format(d="20260310"), seed=2, clearing=True)
    aoi = AOI(id="test", name="Caso de prueba", role="flagship", status="approximate",
              bbox=(-70.29, -12.70, -70.18, -12.62), phenomena=["deforestation"])
    monkeypatch.setattr(workflows, "load_aois", lambda: {"test": aoi})
    monkeypatch.setattr(workflows, "load_thresholds", lambda: Thresholds(min_alert_pixels=20))
    monkeypatch.setattr(settings, "PROCESSED", tmp_path / "processed")
    monkeypatch.setattr(main, "PROCESSED", settings.PROCESSED)
    layer = workflows.change_between("test", before, after)["manifest"]["id"]
    client = TestClient(app)
    for stage in ("change", "before", "after"):
        response = client.get(f"/api/tiles/{layer}/{stage}/0/0/0.png")
        assert response.status_code == 200
        with MemoryFile(response.content) as source, source.open() as image:
            assert image.driver == "PNG"
    outside = client.get(f"/api/tiles/{layer}/before/4/0/0.png")
    with MemoryFile(outside.content) as source, source.open() as image:
        assert image.read(4).max() == 0
