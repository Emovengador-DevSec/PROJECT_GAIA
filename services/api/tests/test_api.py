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


def test_remediation_endpoints(tmp_path, monkeypatch):
    c = TestClient(main.app)
    assert c.get("/api/remediation/invalid_aoi!").status_code == 422
    assert c.get("/api/remediation/no-such-aoi").status_code == 404

    # Mock published directory with synthetic remediation data
    published = tmp_path / "04_published" / "remediation"
    published.mkdir(parents=True)
    fake_remediation = {
        "aoi_id": "test-zone",
        "summary": {"total_alerts": 1, "high": 0, "medium": 0, "low": 1},
        "alerts": [
            {
                "alert_id": "alr_001",
                "risk_id": "incendio_sequia",
                "level": "bajo",
                "index": 0.25,
            }
        ],
    }
    (published / "test-zone.json").write_text(json.dumps(fake_remediation), encoding="utf-8")
    monkeypatch.setattr(main, "PROCESSED", tmp_path / "03_processed")
    assert c.get("/api/remediation/test-zone").status_code == 200
    res = c.get("/api/remediation/test-zone").json()
    assert res["summary"]["total_alerts"] == 1

    # Single zone detail
    assert c.get("/api/remediation/test-zone/alr_001").status_code == 200
    detail = c.get("/api/remediation/test-zone/alr_001").json()
    assert detail["risk_id"] == "incendio_sequia"
    assert c.get("/api/remediation/test-zone/non-existent").status_code == 404
