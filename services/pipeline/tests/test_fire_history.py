"""A complete query archive distinguishes no detections from missing data."""
from datetime import date

import pytest

from sarlab_pipeline.fire_history import aggregate


def test_archive_deduplicates_detections_and_requires_every_day(tmp_path):
    path = tmp_path / "FIRMS_MODIS_SP_ayacucho-huanta_2001-01-01_5.csv"
    path.write_text("latitude,longitude,acq_date,acq_time,satellite,version\n"
                    "-13.1,-74.1,2001-01-02,1200,Terra,6.1\n"
                    "-13.1,-74.1,2001-01-02,1200,Terra,6.1\n", encoding="utf-8")
    result = aggregate([path], date(2001, 1, 1), date(2001, 1, 5))
    assert result["count"] == 1 and result["covered_days"] == 5
    assert sum(row["count"] for row in result["annual"]) == 1
    assert sum(row["total"] for row in result["monthly"]) == 1
    with pytest.raises(ValueError, match="Faltan originales"):
        aggregate([path], date(2001, 1, 1), date(2001, 1, 6))


def test_firms_budget_survives_failed_requests_and_restarts(data_dirs, monkeypatch):
    import json

    from sarlab_pipeline import settings as S
    from sarlab_pipeline.sources import firms_budget

    clock = [1000.0]
    waits = []
    monkeypatch.setattr(firms_budget.time, "time", lambda: clock[0])
    def sleep(seconds):
        waits.append(seconds)
        clock[0] += seconds
    monkeypatch.setattr(firms_budget.time, "sleep", sleep)
    firms_budget.reserve(5, limit=5, window=60)
    # No successful response/file exists. A fresh call must still wait for the reservation.
    firms_budget.reserve(5, limit=5, window=60)
    assert sum(waits) >= 60
    records = json.loads((S.CATALOG / "firms-transactions.json").read_text())
    assert records == [{"at": 1060.0, "days": 5}]


def test_firms_shared_budget_waits_for_nasa_counter(monkeypatch):
    from sarlab_pipeline.sources import firms_budget

    observations = iter([4900, 3500, 3499])
    waits = []
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"current_transactions": next(observations), "transaction_limit": 5000}
    monkeypatch.setattr(firms_budget.httpx, "get", lambda *args, **kwargs: Response())
    monkeypatch.setattr(firms_budget.time, "sleep", waits.append)
    firms_budget.wait_for_remote_budget("test-key")
    assert waits == [30, 30]
