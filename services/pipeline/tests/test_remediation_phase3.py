"""Pruebas unitarias para la Fase 3: costo-beneficio, escenarios NDVI y constancia PDF.

Usa datos sintéticos exclusivamente para pruebas, cumpliendo la Regla 2.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app import main
from sarlab_pipeline.remediation.certificate_pdf import generate_certificate_pdf
from sarlab_pipeline.remediation.risk import (
    _build_cost_benefit,
    _build_optical_context,
    _build_recovery_scenario,
    compute_risk_for_alert,
)


def test_cost_benefit_hidden_while_unverified():
    budget = [{"cost_total_soles": 4750.0, "minka_discount_pct": 40}]
    assert _build_cost_benefit(crop_ha=2.5, area_ha=4.0, risk_index=0.5, budget=budget) is None


def _verified(monkeypatch):
    from sarlab_pipeline.remediation import risk as r
    cfg = {**r._valuation(), "status": "verificado"}
    monkeypatch.setattr(r, "_valuation", lambda: cfg)


def test_build_cost_benefit_cropland(monkeypatch):
    _verified(monkeypatch)
    budget = [
        {"cost_total_soles": 4750.0, "minka_discount_pct": 40},
        {"cost_total_soles": 5000.0, "minka_discount_pct": 30},
    ]
    cb = _build_cost_benefit(crop_ha=2.5, area_ha=4.0, risk_index=0.5, budget=budget)
    assert cb["currency"] == "PEN"
    assert cb["currency_symbol"] == "S/"
    assert cb["crop_ha_evaluated"] == 2.5
    assert cb["production_value_per_ha_pen"] == 8500.0
    # loss_annual = 2.5 * 8500 * 0.5 = 10625.0
    assert cb["loss_avoided_annual_pen"] == 10625.0
    assert cb["loss_avoided_3yr_pen"] == round(10625.0 * 2.8, 2)
    assert cb["loss_avoided_5yr_pen"] == round(10625.0 * 4.5, 2)
    assert cb["intervention_cost_total_pen"] == 9750.0
    # Minka: 4750*0.6 + 5000*0.7 = 2850 + 3500 = 6350.0
    assert cb["cost_with_minka_pen"] == 6350.0
    assert cb["benefit_cost_ratio_5yr"] > 0
    assert cb["benefit_cost_ratio_minka_5yr"] > cb["benefit_cost_ratio_5yr"]
    assert "MIDAGRI" in cb["valuation_source"]


def test_build_cost_benefit_default_rural(monkeypatch):
    _verified(monkeypatch)
    budget = [{"cost_total_soles": 3000.0, "minka_discount_pct": 35}]
    cb = _build_cost_benefit(crop_ha=0.0, area_ha=1.5, risk_index=0.4, budget=budget)
    assert cb["crop_ha_evaluated"] == 0.0
    assert cb["effective_ha"] == 1.5
    assert cb["production_value_per_ha_pen"] == 3500.0
    assert cb["loss_avoided_annual_pen"] == round(1.5 * 3500 * 0.4, 2)


def test_recovery_scenario_mandatory_label():
    for risk_id in ["incendio_sequia", "erosion_huaico", "ladera_inestable_sismo", "estres_hidrico_agricola"]:
        scen = _build_recovery_scenario(risk_id)
        assert scen["mandatory_label"] == "Escenario con supuestos. No es una observación ni una promesa."
        assert "year_1" in scen["projected"]
        assert "year_3" in scen["projected"]
        assert "year_5" in scen["projected"]
        assert scen["projected"]["year_5"]["ndvi"] > scen["projected"]["year_3"]["ndvi"]
        assert scen["citation"] != ""


def test_optical_context_structure():
    opt = _build_optical_context("ayacucho-huanta")
    assert opt is None  # regional PNGs must not masquerade as zone-specific photos


def test_compute_risk_includes_phase3_fields():
    synthetic_alert = {
        "id": "synthetic_001",
        "aoi_id": "ayacucho-huanta",
        "area_ha": 3.0,
        "hv_drop_db": 3.5,
        "cropland_ha": 1.2,
    }
    res = compute_risk_for_alert(synthetic_alert, slope_deg=30.0)
    assert "cost_benefit" in res
    assert "recovery_scenario" in res
    expected_label = "Escenario con supuestos. No es una observación ni una promesa."
    assert res["recovery_scenario"]["mandatory_label"] == expected_label
    assert res["cost_benefit"] is None  # costs and crop values are still por_verificar


def test_generate_certificate_pdf_structure():
    synthetic_alert = {
        "properties": {
            "id": "alr_synth_test_999",
            "title": "Mancha radar sintética",
            "place": "Valle Huanta",
            "date": "2026-10-10",
            "level": "alto",
            "metrics": {"area_ha": 5.2},
            "granules": ["NISAR_L2_PR_GCOV_SYNTH_01"],
            "date_range": ["2026-06-24", "2026-10-10"],
            "remediation": {
                "risk_name": "Ladera susceptible a erosión hídrica",
                "index": 0.65,
                "factors": {"hv_drop_db": 4.1, "slope_deg": 18.5, "crop_ha": 2.1},
                "budget": [{"name": "Zanjas de infiltración", "cost_total_soles": 4750}],
            },
        }
    }
    pdf_bytes = generate_certificate_pdf(synthetic_alert, aoi_id="ayacucho-huanta")
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert pdf_bytes.strip().endswith(b"%%EOF")
    # Verify presence of mandatory elements in PDF byte stream
    assert b"Constancia de Evidencia Satelital" in pdf_bytes
    assert b"SHA-256" in pdf_bytes


def test_api_certificate_pdf_endpoint(tmp_path, monkeypatch):
    client = TestClient(main.app)

    # 422 on invalid AOI format
    assert client.get("/api/remediation/INVALID_AOI!/zone_1/certificate.pdf").status_code == 422

    # Mock published directory with synthetic remediation data
    published = tmp_path / "04_published" / "remediation"
    published.mkdir(parents=True)
    fake_remediation = {
        "aoi_id": "test-zone",
        "alerts": [
            {
                "alert_id": "alr_synth_01",
                "risk_id": "erosion_huaico",
                "risk_name": "Erosión o huaico",
                "level": "medio",
                "index": 0.45,
                "area_ha": 2.0,
                "factors": {"hv_drop_db": 3.0, "crop_ha": 1.0},
                "budget": [],
                "sources_nisar": {"granules": ["NISAR_SYNTH_A", "NISAR_SYNTH_B"],
                                  "dates": ["2026-06-24", "2026-10-10"]},
            }
        ],
    }
    (published / "test-zone.json").write_text(json.dumps(fake_remediation), encoding="utf-8")
    monkeypatch.setattr(main, "PROCESSED", tmp_path / "03_processed")

    # 404 for unknown zone_id
    assert client.get("/api/remediation/test-zone/non_existent/certificate.pdf").status_code == 404

    # 200 for existing zone_id
    resp = client.get("/api/remediation/test-zone/alr_synth_01/certificate.pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "constancia_test-zone_alr_synth_01.pdf" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"%PDF-1.4")
