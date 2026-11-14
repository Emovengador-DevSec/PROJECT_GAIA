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
    assert "Atención, comunidades de Huanta y La Mar" in script_data["script_es"]
    assert "Aviso de monitoreo. No reemplaza a INDECI" in script_data["script_es"]
    assert "3.5 hectáreas" in script_data["script_es"]
    assert "Pallja" in script_data["script_es"]
    assert 20 <= script_data["duration_es_seconds"] <= 90

    # Quechua Chanka
    assert "Allillanchu ayllukuna" in script_data["script_qu"]
    assert "Kayqa qawapayana willakuymi" in script_data["script_qu"]
    assert "Chanka" in script_data["quechua_metadata"]["variant"]
    assert len(script_data["stations"]) >= 2


def test_generate_minka_call():
    minka = generate_minka_call(SAMPLE_ALERT, aoi_id="ayacucho-huanta")
    assert minka["alert_id"] == "alr_test_001"
    assert minka["primary_place"] == "Pallja"
    assert minka["needed_workers"] >= 15
    assert len(minka["recommended_tools"]) >= 2
    assert "wa.me/?text=" in minka["whatsapp"]["url"]
    assert "🌿 *CONVOCATORIA MINKA COMUNAL" in minka["whatsapp"]["text"]
    assert minka["savings_estimated_soles"] > 0

    # SMS verification preview
    sms = minka["sms_verification"]
    assert sms["mode"] == "preview_only"
    assert "GAIA Alerta" in sms["text"]
    assert sms["char_count"] <= 160


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


def test_api_bulletin_endpoints():
    client = TestClient(app)
    zone_id = "alr_ayacucho-huanta_2026-06-24__2026-10-10_hvhv_000"

    # Bulletin endpoint
    res = client.get(f"/api/remediation/ayacucho-huanta/{zone_id}/bulletin")
    assert res.status_code == 200
    data = res.json()
    assert "bulletin" in data
    assert "minka" in data
    assert "script_es" in data["bulletin"]
    assert "script_qu" in data["bulletin"]

    # Audio endpoint (Spanish)
    res_audio_es = client.get(f"/api/remediation/ayacucho-huanta/{zone_id}/audio.wav?lang=es")
    assert res_audio_es.status_code == 200
    assert res_audio_es.headers["content-type"] == "audio/wav"
    assert res_audio_es.content[:4] == b"RIFF"

    # Audio endpoint (Quechua)
    res_audio_qu = client.get(f"/api/remediation/ayacucho-huanta/{zone_id}/audio.wav?lang=qu")
    assert res_audio_qu.status_code == 200
    assert res_audio_qu.headers["content-type"] == "audio/wav"
    assert res_audio_qu.content[:4] == b"RIFF"

    # Minka commit endpoint
    res_commit = client.post(
        f"/api/remediation/ayacucho-huanta/{zone_id}/minka/commit",
        json={
            "community": "Comunidad Pallja",
            "volunteers": 15,
            "tools": "Picos y barretas",
            "contact_name": "Teniente Gobernador",
        },
    )
    assert res_commit.status_code == 200
    c_data = res_commit.json()
    assert c_data["volunteers"] == 15

    # Commitments list
    res_list = client.get(f"/api/remediation/ayacucho-huanta/{zone_id}/minka/commitments")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1
