"""F5: no fabricated workforce, discount or location in community outputs."""
import json
from pathlib import Path

import pytest

from sarlab_pipeline.remediation.bulletin import generate_minka_call, generate_radio_script


def test_unverified_costs_cannot_leak_source_discount_or_amount(monkeypatch):
    from sarlab_pipeline.remediation import risk

    monkeypatch.setattr(risk, "_costs_cfg", [{
        "id": "test", "status": "estimado", "cost_mid": 100,
        "source": "por_verificar", "minka_discount_pct": 40, "retrieved_date": "2026-01-01",
    }])
    item = risk._build_budget({"interventions": [{"intervention_id": "test"}]}, 3)[0]
    assert item["cost_total_soles"] is None
    assert item["source"] is None
    assert item["minka_discount_pct"] is None


def test_missing_places_suppress_sms_and_do_not_invent_workforce():
    result = generate_minka_call({"alert_id": "test", "area_ha": 1.0})
    assert result["sms_verification"] is None
    assert result["target_communities"] == []
    assert result["needed_workers"] is None
    assert result["estimated_days"] is None
    assert result["savings_estimated_soles"] is None
    assert "comuneros" not in result["whatsapp"]["text"]
    assert "en ." not in result["whatsapp"]["text"]


PUBLISHED = Path(__file__).resolve().parents[3] / "data/04_published/remediation/ayacucho-huanta.json"


@pytest.mark.skipif(not PUBLISHED.exists(), reason="Real published data not installed")
def test_all_real_zone_budgets_and_bulletins_are_supported():
    for zone in json.loads(PUBLISHED.read_text(encoding="utf-8"))["alerts"]:
        places = zone["nearby_places"]
        assert len(places) <= 3
        assert places == sorted(places, key=lambda p: p["distance_m"])
        for item in zone["budget"]:
            if item["status"] != "verificado":
                assert item["cost_total_soles"] is None
                assert item["source"] is None
                assert item["minka_discount_pct"] is None
                assert item["cost_label"] == "costo por confirmar"
        minka = generate_minka_call(zone)
        bulletin = generate_radio_script(zone)
        assert minka["target_communities"] == [p["name"] for p in places]
        if places:
            assert places[0]["name"] in minka["sms_verification"]["text"]
            assert places[0]["name"] in bulletin["script_es"]
        else:
            assert minka["sms_verification"] is None
        assert "en ." not in minka["whatsapp"]["text"]
