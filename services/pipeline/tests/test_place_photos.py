"""Synthetic photo/source fixtures live only in pipeline tests."""

from __future__ import annotations

import copy
import json
from io import BytesIO

import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from sarlab_pipeline import photos, place_imagery

GEOMETRY = {"type": "Polygon", "coordinates": [[[0, 0], [0.01, 0], [0.01, 0.01], [0, 0.01], [0, 0]]]}


def observation():
    return {
        "id": 100,
        "quality_grade": "research",
        "observed_on": "2024-05-01",
        "user": {"login": "observer"},
        "taxon": {"name": "Schinus molle", "iconic_taxon_name": "Plantae"},
        "photos": [
            {"id": 1, "license_code": "cc-by", "url": "https://static.inaturalist.org/photos/1/square.jpg"}
        ],
        "geojson": {"coordinates": [0.005, 0.005]},
        "positional_accuracy": 20,
    }


@pytest.mark.parametrize("license_code", [None, "all rights reserved", "cc-by-nc", "cc-by-nc-sa", "unknown"])
def test_rejects_unclear_or_noncommercial_licenses(license_code):
    data = observation()
    data["photos"][0]["license_code"] = license_code
    assert photos.inat_photo(data, "nearby") is None


@pytest.mark.parametrize(
    "change",
    [
        {"obscured": True},
        {"geoprivacy": "private"},
        {"taxon_geoprivacy": "obscured"},
        {"positional_accuracy": 101},
        {"positional_accuracy": None},
        {"observed_on": None},
        {"quality_grade": "casual"},
        {"user": {}},
        {"geojson": {"coordinates": [500, 95]}},
        {"taxon": {"iconic_taxon_name": "Reptilia"}},
    ],
)
def test_rejects_unverifiable_or_protected_observations(change):
    data = observation()
    data.update(change)
    assert photos.inat_photo(data, "nearby") is None


def test_original_attribution_and_photo_license_are_preserved():
    data = observation()
    data["license_code"] = "cc-by-nc"  # Observation licence differs from its photo licence.
    result = photos.inat_photo(data, "nearby")
    assert result["license"] == "CC-BY"
    assert result["author"] == "observer"
    assert result["taken_at"] == "2024-05-01"
    assert result["source_url"].endswith("/100")
    assert result["remote_url"].endswith("/large.jpg")
    data["photos"][0]["attribution"] = "(c) Photographer, some rights reserved (CC BY)"
    result = photos.inat_photo(data, "nearby")
    assert "Photographer" in result["author"]
    assert result["author_role"] == "Crédito de la foto"


def test_distance_is_to_polygon_and_accounts_for_accuracy():
    assert photos.zone_distance_km(GEOMETRY, 0.005, 0.005) == 0
    assert 0.54 < photos.zone_distance_km(GEOMETRY, 0.015, 0.005) < 0.57
    near = {"role": "nearby", "lon": 0.013, "lat": 0.005, "accuracy_m": 20}
    assert photos.relation(GEOMETRY, near)["location_label"].startswith("Esta zona")
    assert not photos.relation(GEOMETRY, {**near, "accuracy_m": 300})["location_label"].startswith(
        "Esta zona"
    )
    assert not photos.relation(GEOMETRY, {**near, "role": "species"})["location_label"].startswith(
        "Esta zona"
    )
    assert photos.relation(GEOMETRY, {"lat": None, "lon": None})["distance_km"] is None


def test_commons_requires_photo_metadata_and_clear_license():
    page = {
        "pageid": 10,
        "title": "File:Schinus molle.jpg",
        "imageinfo": [
            {
                "mime": "image/jpeg",
                "url": "https://upload.wikimedia.org/image.jpg",
                "descriptionurl": "https://commons.wikimedia.org/wiki/File:test",
                "extmetadata": {
                    "LicenseShortName": {"value": "CC BY-SA 4.0"},
                    "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0/"},
                    "Artist": {"value": '<a href="https://example.test">Photographer</a>'},
                    "DateTimeOriginal": {"value": "2020-01-01"},
                },
            }
        ],
    }
    assert photos.commons_photo(page, "species")["author"] == "Photographer"
    for field in ["Artist", "DateTimeOriginal", "LicenseShortName", "LicenseUrl"]:
        invalid = copy.deepcopy(page)
        del invalid["imageinfo"][0]["extmetadata"][field]
        assert photos.commons_photo(invalid, "species") is None


def test_collector_stores_only_local_resized_images(tmp_path, monkeypatch):
    stream = BytesIO()
    Image.new("RGB", (1600, 1200), "green").save(stream, "JPEG")
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, content=stream.getvalue(), headers={"Content-Type": "image/jpeg"})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        collector = photos.Collector(tmp_path, client)
        candidate = photos.inat_photo(observation(), "nearby")
        result = collector.store(candidate)
        assert result["image_url"] == "/api/photos/images/inat-1.jpg"
        assert "remote_url" not in result
        with Image.open(tmp_path / "images/inat-1.jpg") as image:
            assert max(image.size) == 800
        with Image.open(tmp_path / "images/inat-1-thumb.jpg") as image:
            assert max(image.size) == 96
        collector.store(candidate)
        assert len(requests) == 1
        assert collector.store({**candidate, "id": "../../escape"}) is None
        assert collector.store({**candidate, "remote_url": "http://127.0.0.1/private"}) is None
        assert collector.store({**candidate, "license": "CC-BY-NC"}) is None
        monkeypatch.setattr(photos, "MAX_IMAGE_BYTES", 1)
        assert collector.store({**candidate, "id": "inat-2"}) is None


def test_api_queries_are_cached_and_stop_on_remote_refusal(tmp_path, monkeypatch):
    monkeypatch.setattr(photos.time, "sleep", lambda _: None)
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(403 if "denied" in str(request.url) else 200, json={"results": []})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        collector = photos.Collector(tmp_path, client)
        assert collector.get_json("https://api.inaturalist.org/example", {}) == {"results": []}
        assert collector.get_json("https://api.inaturalist.org/example", {}) == {"results": []}
        assert len(requests) == 1
        assert collector.get_json("https://commons.wikimedia.org/denied", {}) == {}
        assert collector.get_json("https://commons.wikimedia.org/denied2", {}) == {}
        assert len(requests) == 2
        assert collector.errors


def test_crop_uses_recorded_transform_and_distinct_polygon_contours():
    bounds = [-0.01, -0.01, 0.04, 0.04]
    image = Image.new("RGBA", (300, 300), (50, 150, 20, 255))
    before, actual_bounds = place_imagery.outlined_crop(image, bounds, GEOMETRY)
    other = {"type": "Polygon", "coordinates": [[[0.02, 0.02], [0.03, 0.02], [0.025, 0.03], [0.02, 0.02]]]}
    after, _ = place_imagery.outlined_crop(image, bounds, other)
    assert before.tobytes() != after.tobytes()
    assert actual_bounds[0] < 0 < actual_bounds[2]
    assert actual_bounds[1] < 0 < actual_bounds[3]
    pixels = np.asarray(before)
    assert ((pixels[:, :, 0] > 200) & (pixels[:, :, 1] > 170) & (pixels[:, :, 2] < 100)).any()
    with pytest.raises(ValueError, match="sale"):
        place_imagery.outlined_crop(image, [0, 0, 0.01, 0.01], GEOMETRY)
    assert not place_imagery.usable_pixels(Image.new("RGBA", (20, 20), (0, 0, 0, 0)))
    assert not place_imagery.usable_pixels(Image.new("RGBA", (20, 20), (50, 150, 20, 255)))


def test_historical_cloud_filter_is_checked_even_if_remote_filter_is_ignored():
    class FakeCatalogue:
        def get_json(self, *_):
            entry = {
                "time_start": "2016-01-02T00:00:00Z",
                "producer_granule_id": "real-scene",
                "id": "G1",
                "polygons": [["-1 -1 -1 1 1 1 1 -1 -1 -1"]],
            }
            return {"feed": {"entry": [{**entry, "cloud_cover": "65"}, {**entry, "cloud_cover": "3"}]}}

    result = place_imagery.historic_scene(FakeCatalogue(), [0, 0, 0.1, 0.1])
    assert result["cloud_cover_pct"] == 3


def test_local_api_catalogue_and_traversal_protection(tmp_path, monkeypatch):
    from fastapi import HTTPException

    import app.main as main
    from app.place_photos import photo_file

    monkeypatch.setattr(main, "PROCESSED", tmp_path / "03_processed")
    published = tmp_path / "04_published"
    (published / "remediation").mkdir(parents=True)
    zone = {"alert_id": "zone_1", "geometry": GEOMETRY, "recipe": {}, "soil": None}
    (published / "remediation/test.json").write_text(json.dumps({"alerts": [zone]}))
    client = TestClient(main.app)
    result = client.get("/api/remediation/test/zone_1/place")
    assert result.status_code == 200
    assert result.json()["available"] is False
    assert result.json()["pins"] == []
    assert client.get("/api/remediation/test/unknown/place").status_code == 404
    assert client.get("/api/remediation/test/zone_1/imagery/past.png").status_code == 404
    with pytest.raises(HTTPException):
        photo_file("..\\..\\secret.jpg")
    assert client.get("/api/photos/images/missing.jpg").status_code == 404


def test_reviewed_reference_sources_are_supported_without_opening_arbitrary_hosts(tmp_path):
    stream = BytesIO()
    Image.new("RGB", (30, 30), "brown").save(stream, "JPEG")
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=stream.getvalue()))
    ) as client:
        collector = photos.Collector(tmp_path, client)
        reference = {
            **photos.inat_photo(observation(), "nearby"),
            "id": "reference-aaaaaaaaaaaa",
            "role": "soil",
            "source_url": "https://wrb.isric.org/picture-gallery.html",
            "remote_url": "https://wrb.isric.org/images/example.jpg",
        }
        assert collector.store(reference)["image_url"].endswith("reference-aaaaaaaaaaaa.jpg")
        reference.update(
            id="reference-bbbbbbbbbbbb",
            source_url="https://www.flickr.com/photos/example/1",
            remote_url="https://api.openverse.org/v1/images/example/thumb/",
        )
        assert collector.store(reference)
        assert (
            collector.store(
                {**reference, "id": "reference-cccccccccccc", "remote_url": "https://evil.test/photo.jpg"}
            )
            is None
        )
