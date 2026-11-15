"""Audit real published photographic evidence; does not download or create data."""
from __future__ import annotations

import hashlib
import json
from collections import Counter

from sarlab_pipeline.photos import photo_license, relation, zone_distance_km
from sarlab_pipeline.settings import PUBLISHED


def main():
    aoi = "ayacucho-huanta"
    data = json.loads((PUBLISHED / "photos" / f"{aoi}.json").read_text(encoding="utf-8"))
    remediation = json.loads((PUBLISHED / "remediation" / f"{aoi}.json").read_text(encoding="utf-8"))
    zones = {z["alert_id"]: z for z in remediation["alerts"]}
    for photo in data["photos"].values():
        assert all(photo.get(key) for key in ("author", "taken_at", "license", "license_url", "source_url"))
        assert photo_license(photo["license"], photo["license_url"])
        assert photo["image_url"].startswith("/api/photos/images/")
        assert "remote_url" not in photo
        assert (PUBLISHED / "photos/images" / f"{photo['id']}.jpg").is_file()
        assert (PUBLISHED / "photos/images" / f"{photo['id']}-thumb.jpg").is_file()
    claims = 0
    for zone_id, evidence in data["zones"].items():
        for pid in evidence["nearby"]:
            photo = data["photos"][pid]
            distance = zone_distance_km(zones[zone_id]["geometry"], photo["lon"], photo["lat"])
            assert distance <= 5
            assert photo["accuracy_m"] <= 100
            text = relation(zones[zone_id]["geometry"], photo)["location_label"]
            if text.startswith("Esta zona"):
                assert distance + photo["accuracy_m"] / 1000 < .5
                claims += 1
    images = json.loads((PUBLISHED / "place-imagery" / aoi / "catalog.json").read_text(encoding="utf-8"))
    counts = Counter()
    for zone_id, moments in images["zones"].items():
        for moment, image in moments.items():
            if not image["available"]:
                assert image["reason"]
                continue
            assert image["crs"] == "EPSG:4326" and image["resolution_m"] == 30
            assert all(image.get(key) for key in ("author", "date", "license", "license_url", "source_url"))
            assert "BBOX=" in image["source_url"] and "TIME=" in image["source_url"]
            assert (PUBLISHED / "place-imagery" / aoi / zone_id / f"{moment}.png").is_file()
            if moment == "past":
                assert 2016 <= int(image["date"][:4]) <= 2018
                assert image["scene_metadata"]["cloud_cover_pct"] <= 5
            counts[moment] += 1
    hashes = []
    for cause in ["incendio_sequia", "erosion_huaico", "estres_hidrico_agricola"]:
        zone_id = next(z["alert_id"] for z in zones.values() if z["risk_id"] == cause)
        hashes.append(hashlib.sha256((PUBLISHED / "place-imagery" / aoi / zone_id / "after.png").read_bytes()).hexdigest())
    assert len(set(hashes)) == 3
    print(json.dumps({"photos_with_credits_and_licenses": len(data["photos"]),
                      "species_with_photos": sum(bool(s["photo_id"]) for s in data["species"]),
                      "zones": len(zones), "within_500m_claims_checked": claims,
                      "images": dict(counts), "three_distinct_cause_crops": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
