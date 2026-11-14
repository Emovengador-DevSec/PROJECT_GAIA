"""Tests for Phase 2: Climate normals, Open-Meteo anomaly detection, and smart agricultural calendar.

Uses synthetic data only — no real network calls, no external APIs.
"""

from __future__ import annotations

from datetime import date

import pytest

from sarlab_pipeline.remediation.open_meteo import (
    detect_climate_anomalies,
    evaluate_agricultural_calendar,
)


@pytest.fixture
def synthetic_season():
    return {
        "season_code": "SON",
        "season_name": "Primavera (septiembre–noviembre)",
        "typical_tmax_c": 21.0,
        "typical_tmin_c": 5.0,
        "typical_rain_mm": 45.0,
        "p10_tmin_c": 2.5,
        "p90_tmax_c": 23.0,
        "p90_rain_daily_mm": 12.0,
        "units": {"temperature": "°C", "rainfall": "mm"},
    }


class TestClimateAnomalyDetection:
    def test_empty_forecast_returns_no_anomalies(self, synthetic_season):
        assert detect_climate_anomalies(None, synthetic_season) == []
        assert detect_climate_anomalies({}, synthetic_season) == []

    def test_heat_anomaly_triggered_when_exceeding_p90(self, synthetic_season):
        forecast = {
            "daily": {
                "time": ["2026-11-20"],
                "temperature_2m_max": [25.5],  # > 23.0 P90
                "temperature_2m_min": [6.0],
                "precipitation_sum": [0.0],
            }
        }
        anomalies = detect_climate_anomalies(forecast, synthetic_season)
        assert len(anomalies) == 1
        assert "calor" in anomalies[0]["title"].lower()
        assert anomalies[0]["metrics"]["tmax_c"] == 25.5
        assert anomalies[0]["source"] == "Clima · Open-Meteo / NASA POWER"

    def test_frost_anomaly_triggered_when_below_p10(self, synthetic_season):
        forecast = {
            "daily": {
                "time": ["2026-11-21"],
                "temperature_2m_max": [18.0],
                "temperature_2m_min": [1.2],  # < 2.5 P10
                "precipitation_sum": [0.0],
            }
        }
        anomalies = detect_climate_anomalies(forecast, synthetic_season)
        assert len(anomalies) == 1
        assert "helada" in anomalies[0]["title"].lower()
        assert anomalies[0]["metrics"]["tmin_c"] == 1.2

    def test_extreme_frost_triggered_for_livestock(self, synthetic_season):
        forecast = {
            "daily": {
                "time": ["2026-11-22"],
                "temperature_2m_max": [14.0],
                "temperature_2m_min": [-4.5],  # <= -3.0
                "precipitation_sum": [0.0],
            }
        }
        anomalies = detect_climate_anomalies(forecast, synthetic_season)
        assert len(anomalies) == 1
        assert "severa" in anomalies[0]["title"].lower()
        assert anomalies[0]["level"] == "alto"
        assert "ganado" in anomalies[0]["title"].lower() or "ganado" in anomalies[0]["note"].lower()

    def test_heavy_rainfall_triggered_above_threshold(self, synthetic_season):
        forecast = {
            "daily": {
                "time": ["2026-11-23"],
                "temperature_2m_max": [19.0],
                "temperature_2m_min": [6.0],
                "precipitation_sum": [25.0],  # > 20 mm threshold and > 12 mm P90
            }
        }
        anomalies = detect_climate_anomalies(forecast, synthetic_season)
        assert len(anomalies) == 1
        assert "lluvia intensa" in anomalies[0]["title"].lower()
        assert anomalies[0]["metrics"]["rain_mm"] == 25.0


class TestAgriculturalCalendar:
    def test_all_four_crops_evaluated(self, synthetic_season):
        forecast = {
            "daily": {
                "time": [f"2026-11-{i:02d}" for i in range(14, 21)],
                "temperature_2m_max": [19.0] * 7,
                "temperature_2m_min": [6.0] * 7,
                "precipitation_sum": [3.0] * 7,
                "soil_moisture_0_to_10cm_mean": [0.22] * 7,
            }
        }
        result = evaluate_agricultural_calendar(
            forecast, synthetic_season, current_date=date(2026, 11, 14)
        )
        crop_ids = [c["id"] for c in result["crops"]]
        assert "papa" in crop_ids
        assert "maiz" in crop_ids
        assert "quinua" in crop_ids
        assert "habas" in crop_ids
        assert "livestock" in result
        assert "promoter_note" in result

    def test_favorable_sowing_in_season(self, synthetic_season):
        forecast = {
            "daily": {
                "time": [f"2026-11-{i:02d}" for i in range(14, 21)],
                "temperature_2m_max": [20.0] * 7,
                "temperature_2m_min": [7.0] * 7,
                "precipitation_sum": [5.0] * 7,
                "soil_moisture_0_to_10cm_mean": [0.24] * 7,
            }
        }
        result = evaluate_agricultural_calendar(
            forecast, synthetic_season, current_date=date(2026, 11, 14)
        )
        papa = next(c for c in result["crops"] if c["id"] == "papa")
        assert papa["status"] == "favorable"
        assert "favorables para siembra" in papa["guidance"]

    def test_frost_warning_for_sensitive_crops(self, synthetic_season):
        forecast = {
            "daily": {
                "time": [f"2026-11-{i:02d}" for i in range(14, 21)],
                "temperature_2m_max": [15.0] * 7,
                "temperature_2m_min": [-1.0] + [5.0] * 6,  # Frost event
                "precipitation_sum": [0.0] * 7,
                "soil_moisture_0_to_10cm_mean": [0.20] * 7,
            }
        }
        result = evaluate_agricultural_calendar(
            forecast, synthetic_season, current_date=date(2026, 11, 14)
        )
        maiz = next(c for c in result["crops"] if c["id"] == "maiz")
        assert maiz["status"] == "precaucion"
        assert "helada" in maiz["guidance"].lower()

    def test_out_of_season_marked(self, synthetic_season):
        # In May (month 5), maize sowing is out of season
        result = evaluate_agricultural_calendar(
            None, synthetic_season, current_date=date(2026, 5, 10)
        )
        maiz = next(c for c in result["crops"] if c["id"] == "maiz")
        assert maiz["status"] == "fuera_de_temporada"
