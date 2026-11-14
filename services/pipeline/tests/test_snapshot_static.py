"""Verifica la exportación estática con una API sintética aislada de los datos reales."""
import importlib.util
import json
import sys
from base64 import b64decode
from pathlib import Path

import httpx
import pytest

spec = importlib.util.spec_from_file_location("snapshot_static", Path(__file__).resolve().parents[3]
                                            / "tools" / "snapshot_static.py")
snapshot = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = snapshot
spec.loader.exec_module(snapshot)
PNG = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4nGNg"
                "AAIAAAUAAXpeqz8AAAAASUVORK5CYII=")


def fake_api(extra=None):
    zone = "ayacucho-huanta"
    layers = [{"id": "layer_" + pol, "aoi_id": zone, "dates": {"a": "2026-06-24", "b": "2026-10-10"},
               "kind": "backscatter_diff_db", "cog_path": "C:/private/change.tif",
               "comparison": {"before_cog_path": "C:/private/before.tif", "range": {"min": -30, "max": 0}},
               "provenance": {"granules": ["before.h5", "after.h5"], "layer": pol, "frequency": "frequencyA"}}
              for pol in ("HHHH", "HVHV")]

    def handle(request):
        path = request.url.path
        if path.endswith(".png"):
            return httpx.Response(200, content=PNG, headers={"content-type": "image/png"})
        payload = None
        if path == "/api/aois":
            payload = [{"id": zone, "bbox": [-74.4, -13.4, -73.9, -12.8]}]
        elif path == "/api/layers":
            payload = layers
        elif path == "/api/health":
            payload = {"tiles": True, "credentials": {"earthdata": True}, "status": "ok"}
        elif path == "/api/config":
            payload = extra or {"features": {"globe": True}}
        elif path.startswith("/api/polarizations") or path.startswith("/api/context"):
            payload = []
        elif path == "/api/alerts":
            payload = {"type": "FeatureCollection", "features": [], "sources": []}
        elif path == "/api/timeseries":
            payload = {"aoi_id": zone, "samples": []}
        elif path == "/api/stories/" + zone:
            payload = {"title": "Relato de prueba", "steps": []}
        return httpx.Response(200, content=json.dumps(payload), headers={"content-type": "application/json"})
    return httpx.Client(base_url="http://127.0.0.1:8000", transport=httpx.MockTransport(handle))


def test_export_publishes_complete_tiles_and_sanitizes_server_paths(tmp_path):
    target = tmp_path / "snapshot"
    with fake_api() as client:
        manifest = snapshot.export_snapshot(client, target, maximum=0, workers=1)
    assert len(list(target.rglob("*.png"))) == 10
    assert manifest["tiles"]["maximum_level"] == 0
    route = snapshot.canonical("/timeseries?aoi=ayacucho-huanta&allow_empty=true")
    assert route in manifest["responses"]
    layers = json.loads((target / "api/layers.json").read_text())
    assert layers[0]["provenance"]["granules"] == ["before.h5", "after.h5"]
    assert "cog_path" not in layers[0]
    assert "before_cog_path" not in layers[0]["comparison"]
    health = json.loads((target / "api/health.json").read_text())
    assert health["offline"] and health["credentials"] == {"earthdata": False, "firms": False}
    assert manifest["total_bytes"] == sum(item["size_bytes"] for item in manifest["files"])
    for item in manifest["files"]:
        assert (target / item["path"]).stat().st_size == item["size_bytes"]
    with fake_api() as client:
        snapshot.export_snapshot(client, target, maximum=0, workers=1)
    assert not list(tmp_path.glob(".snapshot-*"))


@pytest.mark.parametrize("payload", [{"EARTHDATA_TOKEN": "private"}, {"key": "private"},
                                      {"apiKey": "private"}, {"mapKey": "private"},
                                      {"url": "https://example.test/data?MAP_KEY=private"},
                                      {"url": "https://example.test/data?X-Amz-Signature=private"},
                                      {"url": "https://example.test/data?X-Amz-Credential=private"},
                                      {"url": "https://example.test/data?sig=private"},
                                      {"text": "C:/Users/private/file"}])
def test_sensitive_data_aborts_before_replacing_previous_snapshot(tmp_path, payload):
    target = tmp_path / "snapshot"
    target.mkdir()
    marker = target / "previous.txt"
    marker.write_text("previous complete snapshot")
    with fake_api(payload) as client, pytest.raises(ValueError, match="sensible|privado|credenciales"):
        snapshot.export_snapshot(client, target, maximum=0, workers=1)
    assert marker.read_text() == "previous complete snapshot"
    assert not (target / "manifest.json").exists()


def test_tile_bounds_and_local_api_reject_unsafe_inputs():
    assert list(snapshot.tile_coordinates([-74.4, -13.4, -73.9, -12.8], 0)) == [(0, 0, 0)]
    assert snapshot.canonical("/alerts?include_live=true&active_only=true") == (
        "/alerts?active_only=true&include_live=true")
    for url in ("https://example.com", "http://127.0.0.1:8000/?token=x", "http://user:pass@localhost"):
        with pytest.raises(ValueError):
            snapshot.local_api(url)
    with pytest.raises(ValueError):
        list(snapshot.tile_coordinates([170, -10, -170, 10], 2))
