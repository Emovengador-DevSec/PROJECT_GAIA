import json

from fastapi.testclient import TestClient

import app.main as main


def test_health_and_config():
    c = TestClient(main.app)
    assert c.get("/api/health").json()["status"] == "ok"
    cfg = c.get("/api/config").json()
    assert "features" in cfg and "EARTHDATA_TOKEN" not in json.dumps(cfg)


def test_aois_listed():
    ids = {a["id"] for a in TestClient(main.app).get("/api/aois").json()}
    assert "madre-de-dios-la-pampa" in ids


def test_layers_read_manifests(tmp_path, monkeypatch):
    d = tmp_path / "zona-x" / "gcov" / "2025-11-22__2026-03-10"; d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"id": "lyr_a", "aoi_id": "zona-x"}))
    (d / "alerts.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [{"x": 1}]}))
    monkeypatch.setattr(main, "PROCESSED", tmp_path)
    c = TestClient(main.app)
    assert c.get("/api/layers?aoi=zona-x").json()[0]["id"] == "lyr_a"
    assert c.get("/api/layers/nope").status_code == 404
    assert len(c.get("/api/alerts?aoi=zona-x").json()["features"]) == 1
    assert c.get("/api/alerts?aoi=../etc").status_code == 422


def test_story_and_timeseries(tmp_path, monkeypatch):
    c = TestClient(main.app)
    st = c.get("/api/stories/madre-de-dios-la-pampa").json()
    assert st["hypotheses"] and st["steps"]
    assert c.get("/api/stories/no-existe").status_code == 404
    monkeypatch.setattr(main, "PROCESSED", tmp_path)
    assert c.get("/api/timeseries?aoi=zona-x").status_code == 404
    d = tmp_path / "zona-x" / "gcov"; d.mkdir(parents=True)
    (d / "timeseries.json").write_text(json.dumps({"samples": [1, 2]}))
    assert c.get("/api/timeseries?aoi=zona-x").json()["samples"] == [1, 2]
