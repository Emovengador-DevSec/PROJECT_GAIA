"""Tests for Phase 4: GAIA Voz radio bulletin, Minka Digital and last-mile alerts.

Uses synthetic test alert structures and mock files.
Tests:
- generate_radio_script (Spanish, Quechua Chanka, mandatory notices, duration)
- generate_minka_call (WhatsApp share link, workers, tools, SMS preview)
- synthesize_bulletin_audio_wav (valid RIFF/WAVE header and bytes)
- add_commitment / get_commitments
- FastAPI endpoints for bulletin, audio, and commitments
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from sarlab_pipeline.remediation.bulletin import (
    add_commitment,
    generate_minka_call,
    generate_radio_script,
    get_commitments,
    synthesize_bulletin_audio_wav,
)

SAMPLE_ALERT = {
    "alert_id": "alr_test_001",
    "area_ha": 3.5,
    "level": "alto",
    "factors": {
        "slope_deg": 24.0,
        "crop_ha": 2.1,
    },
    "exposure": {
        "places": ["Pallja", "Ccochapunco", "Pampa Corral"],
        "nearby_places": [{"name": "Pallja", "distance_m": 100},
                          {"name": "Ccochapunco", "distance_m": 200}],
    },
    "risk": {
        "dominant_risk": "erosion_huaico",
        "dominant_risk_name": "Erosión o huaico en ladera",
    },
    "recipe": {
        "risk_name": "Zanjas de infiltración y reforestación de contención",
        "species_primary": ["Queñua (Polylepis)", "Colle (Buddleja coriacea)", "Ichu"],
        "interventions": [
            {"intervention_id": "zanjas_infiltracion", "priority": 1},
        ],
    },
    "costs": {
        "cost_total_soles": 8500.0,
    },
    "cost_benefit": {
        "minka_savings_soles": 3400.0,
    },
}


def test_generate_radio_script_spanish_and_quechua():
    script_data = generate_radio_script(SAMPLE_ALERT, aoi_id="ayacucho-huanta")
    assert script_data["alert_id"] == "alr_test_001"
    assert "Atención, comunidades" in script_data["script_es"]
    assert "Aviso de monitoreo. No reemplaza a INDECI" in script_data["script_es"]
    assert "3.5 hectáreas" in script_data["script_es"]
    assert "Pallja" in script_data["script_es"]
    assert 20 <= script_data["duration_es_seconds"] <= 90

    # Quechua Chanka
    assert "Allillanchu ayllukuna" in script_data["script_qu"]
    assert "Kayqa qawapayana willakuymi" in script_data["script_qu"]
    assert "Chanka" in script_data["quechua_metadata"]["variant"]
    # Unreviewed Quechua must say so; no unconfirmed radio stations are listed
    assert script_data["quechua_metadata"]["reviewed"] is False
    assert script_data["stations"] == []


def test_generate_minka_call():
    minka = generate_minka_call(SAMPLE_ALERT, aoi_id="ayacucho-huanta")
    assert minka["alert_id"] == "alr_test_001"
    assert minka["primary_place"] == "Pallja"
    assert minka["needed_workers"] is None
    assert minka["estimated_days"] is None
    assert "wa.me/?text=" in minka["whatsapp"]["url"]
    assert "PROPUESTA MINKA COMUNAL" in minka["whatsapp"]["text"]
    assert minka["savings_estimated_soles"] is None

    # SMS verification preview
    sms = minka["sms_verification"]
    assert sms["mode"] == "preview_only"
    assert "GAIA Alerta" in sms["text"]
    assert sms["char_count"] == len(sms["text"])


def test_synthesize_bulletin_audio_wav():
    wav_bytes = synthesize_bulletin_audio_wav("Atención comunidades de Huanta. Aviso de monitoreo.")
    assert len(wav_bytes) >= 44
    assert wav_bytes[:4] == b"RIFF"
    assert wav_bytes[8:12] == b"WAVE"


def test_commitments_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_file = Path(tmpdir) / "commitments.json"
        with patch("sarlab_pipeline.remediation.bulletin.COMMITMENTS_FILE", tmp_file):
            item = add_commitment(
                aoi_id="ayacucho-huanta",
                zone_id="alr_test_001",
                community="Pallja Alta",
                volunteers=12,
                tools="12 picos y 6 palas",
                contact_name="Juan Quispe",
            )
            assert item["community"] == "Pallja Alta"
            assert item["volunteers"] == 12

            listed = get_commitments("ayacucho-huanta", "alr_test_001")
            assert len(listed) == 1
            assert listed[0]["volunteers"] == 12


def test_api_bulletin_endpoints(tmp_path, monkeypatch):
    import json

    from app import main
    from sarlab_pipeline.remediation import bulletin as b

    published = tmp_path / "04_published" / "remediation"
    published.mkdir(parents=True)
    zone_id = "alr_synth_01"
    (published / "test-zone.json").write_text(json.dumps({"alerts": [{**SAMPLE_ALERT, "alert_id": zone_id}]}),
                                              encoding="utf-8")
    monkeypatch.setattr(main, "PROCESSED", tmp_path / "03_processed")
    monkeypatch.setattr(b, "COMMITMENTS_FILE", published / "commitments.json")
    client = TestClient(app)

    res = client.get(f"/api/remediation/test-zone/{zone_id}/bulletin")
    assert res.status_code == 200
    data = res.json()
    assert "script_es" in data["bulletin"] and "script_qu" in data["bulletin"]
    assert data["audio_url_qu"] is None  # no speaker recording yet

    # Quechua is never synthesized
    assert client.get(f"/api/remediation/test-zone/{zone_id}/audio.wav?lang=qu").status_code == 404

    # Minka: unknown zones are rejected; contact names never leave the server
    body = {"community": "Comunidad X", "volunteers": 15, "tools": "Picos", "contact_name": "Persona"}
    assert client.post("/api/remediation/test-zone/zona-inventada/minka/commit", json=body).status_code == 404
    res_commit = client.post(f"/api/remediation/test-zone/{zone_id}/minka/commit", json=body)
    assert res_commit.status_code == 200
    assert "contact_name" not in res_commit.json()
    listed = client.get(f"/api/remediation/test-zone/{zone_id}/minka/commitments").json()
    assert len(listed) == 1 and "contact_name" not in listed[0]
