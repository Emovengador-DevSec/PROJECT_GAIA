"""Community rules and public report privacy with isolated test data."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import community, live, main, reports

NOW = datetime(2026, 11, 14, 12, tzinfo=UTC)


def feed(hours=None, **metrics):
    features = [] if hours is None else [{
        "geometry": {"type": "Point", "coordinates": [-74.15, -13.1]},
        "properties": {"date": (NOW - timedelta(hours=hours)).isoformat(), "metrics": metrics},
    }]
    return {"status": "ok", "stale": False, "last_updated": NOW.isoformat(), "features": features}


@pytest.mark.parametrize(
    ("fires", "quakes", "weather", "expected"),
    [
        (feed(1), feed(), {"heat_days": 3, "rain_ratio": 0.2}, "red"),
        (feed(72), feed(), {"heat_days": 0, "rain_ratio": 1.0}, "orange"),
        (feed(), feed(2, magnitude=4.5), {"heat_days": 0, "rain_ratio": 1.0}, "orange"),
        (feed(), feed(), {"heat_days": 3, "rain_ratio": 0.2}, "orange"),
        (feed(), feed(), {"heat_days": 0, "rain_ratio": 0.49}, "yellow"),
        (feed(), feed(), {"heat_days": 0, "rain_ratio": 2.0}, "orange"),
        (feed(), feed(), {"heat_days": 0, "rain_ratio": 4.03}, "orange"),
        (feed(), feed(), {"heat_days": 0, "rain_ratio": 1.99}, "green"),
        (feed(), feed(), {"date": "2026-10-14", "heat_days": 0, "rain_ratio": 4.03}, "unavailable"),
        (feed(), feed(2, magnitude=4.4), {"heat_days": 2, "rain_ratio": 0.5}, "green"),
        ({**feed(), "stale": True}, feed(), {"heat_days": 0, "rain_ratio": 1.0}, "unavailable"),
        (feed(), feed(), None, "unavailable"),
        (feed(), feed(), {"date": "2026-10-14", "heat_days": 4, "rain_ratio": 0.3}, "unavailable"),
    ],
)
def test_indicator_observed_rules(fires, quakes, weather, expected):
    settings = main._yaml(main.CONFIG / "thresholds.yaml")["community"]
    data = {"current": {"date": "2026-11-14", **weather}} if weather else None
    result = community.community_detail({"center": [-74.15, -13.1]}, {"fires": fires, "quakes": quakes},
                                        settings, data, now=NOW)
    assert result["indicator"]["level"] == expected


def test_report_privacy_and_moderation(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "PROCESSED", tmp_path / "03_processed")
    monkeypatch.setattr(reports, "HISTORY", reports.OrderedDict())
    monkeypatch.setattr(live, "collection", lambda _provider: feed())
    monkeypatch.setenv("GAIA_REPORTS_ADMIN_TOKEN", "test-moderator")
    client = TestClient(main.app)
    url = "/api/reports"
    moderator = {"Authorization": "Bearer test-moderator"}
    report = {"kind": "fire", "lon": -74.1517, "lat": -13.1021,
              "observed_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat(), "note": "Nota privada"}
    assert client.get(url).json() == []
    assert client.post(url, json={**report, "note": "contacto@email.com"}).status_code == 422
    assert client.post(url, json={**report, "lon": -70}).status_code == 422
    assert client.post(url, json=report, headers={"Origin": "https://otro.test"}).status_code == 403
    result = client.post(url, json=report)
    assert result.status_code == 201
    assert client.get(url).json() == []
    assert client.get(url + "/moderation").status_code == 403
    assert client.get(url + "/moderation", headers=moderator).json()[0]["note"] == "Nota privada"
    action = url + "/moderation/" + result.json()["id"]
    assert client.patch(action + "?action=visible", headers=moderator).status_code == 204
    public = client.get(url)
    assert public.headers["cache-control"] == "no-store"
    assert public.json()[0]["lon"] == -74.15 and "note" not in public.json()[0]
    assert client.patch(action + "?action=rejected", headers=moderator).status_code == 204
    assert client.get(url).json() == []
    for _ in range(2):
        assert client.post(url, json=report).status_code == 201
    assert client.post(url, json=report).status_code == 429
