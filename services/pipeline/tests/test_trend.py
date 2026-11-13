from app.trend import project


def test_trend_requires_four_distinct_observations():
    series = {
        "samples": [
            {"date": "2026-06-19", "HVHV": {"median_db": -10}},
            {"date": "2026-10-05", "HVHV": {"median_db": -15}},
        ]
    }
    result = project(series, "HVHV")
    assert result["status"] == "insufficient"
    assert result["projection"] == []


def test_robust_projection_has_units_and_uncertainty():
    series = {
        "samples": [
            {"date": f"2026-10-{day:02d}", "HVHV": {"median_db": value}}
            for day, value in ((1, -10), (5, -11), (9, -12), (13, -13), (17, -10))
        ]
    }
    result = project(series, "HVHV")
    assert result["status"] == "ok"
    assert result["dates"] == 5
    assert result["unit"] == "dB"
    assert all(p["low"] <= p["value"] <= p["high"] for p in result["projection"])
    assert "no es una predicción" in result["label"]
