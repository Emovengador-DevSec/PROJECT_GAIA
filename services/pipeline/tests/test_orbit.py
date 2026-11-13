"""Synthetic validation cases stay in the pipeline test tree."""

from datetime import UTC, datetime, timedelta

import pytest

from app import orbit


def _record():
    return {**dict.fromkeys(orbit.NUMBERS, 0), "MEAN_MOTION": 14, "OBJECT_NAME": "NISAR",
            "OBJECT_ID": "test-only", "EPOCH": datetime.now(UTC).replace(tzinfo=None).isoformat()}


def test_orbit_rejects_stale_epoch_nonfinite_and_wrong_satellite():
    assert orbit._validate(_record())["OBJECT_NAME"] == "NISAR"
    for changes in ({"OBJECT_NAME": "OTHER"}, {"BSTAR": float("nan")},
                    {"EPOCH": (datetime.now(UTC) - timedelta(days=8)).isoformat()}):
        with pytest.raises(ValueError):
            orbit._validate({**_record(), **changes})


def test_orbit_failure_is_explicit_without_environment_details(tmp_path, monkeypatch):
    monkeypatch.setattr(orbit, "CACHE", tmp_path / "orbit.json")
    monkeypatch.delenv("SARLAB_OFFLINE", raising=False)

    def fail(_url):
        raise OSError("private upstream diagnostic")

    monkeypatch.setattr(orbit, "_download", fail)
    result = orbit.elements()
    assert result["status"] == "unavailable"
    assert "elements" not in result
    assert "private" not in str(result)
