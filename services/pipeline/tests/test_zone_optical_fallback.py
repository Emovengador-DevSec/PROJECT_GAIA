"""F3 fallback: regional PNGs cannot be presented as georeferenced zone crops."""
import json
from pathlib import Path

import pytest

from sarlab_pipeline.remediation.risk import _build_optical_context


def test_no_zone_can_receive_the_same_regional_photo_as_a_zone_crop():
    assert _build_optical_context("ayacucho-huanta") is None
    assert _build_optical_context("sabancaya") is None


PUBLISHED = Path(__file__).resolve().parents[3] / "data/04_published/remediation/ayacucho-huanta.json"


@pytest.mark.skipif(not PUBLISHED.exists(), reason="Real published data not installed")
def test_published_zones_do_not_advertise_unverified_crops():
    data = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    assert data["alerts"]
    assert all(zone["optical_context"] is None for zone in data["alerts"])
