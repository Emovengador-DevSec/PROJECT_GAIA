"""Boletín radial comunitario «GAIA Voz», Minka Digital y alertas de último kilómetro.

Fase 4 del Plan Maestro (doc 23):
- 4.1 Boletín radial de 30-60 s en español y quechua chanka con voz sintetizada / grabada.
- 4.2 SMS de verificación y vista previa (sin envíos reales sin credenciales ni consentimiento).
- 4.3 Minka Digital comunal compartible por WhatsApp y registro de compromisos.
- 4.4 Yachaq Digital (canal de voz en quechua) como hoja de ruta.
- 4.5 Uso sin conexión para Tambos PAIS.
"""

from __future__ import annotations

import json
import logging
import math
import os
import struct
import subprocess
import tempfile
import urllib.parse
import wave
from datetime import UTC
from pathlib import Path
from typing import Any

import yaml

from .. import settings as S

logger = logging.getLogger(__name__)

CONFIG_DIR = S.DATA_DIR.parent / "config" / "nbs"
COMMITMENTS_FILE = S.DATA_DIR / "04_published" / "remediation" / "commitments.json"


def load_bulletin_config() -> dict[str, Any]:
    """Carga config/nbs/bulletin.yaml con emisoras, formatos y quechua chanka."""
    path = CONFIG_DIR / "bulletin.yaml"
    if path.is_file():
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {}


def load_minka_config() -> dict[str, Any]:
    """Carga config/nbs/minka.yaml con normas de faena comunal y plantillas SMS."""
    path = CONFIG_DIR / "minka.yaml"
    if path.is_file():
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {}


def _get_places_str(alert_data: dict[str, Any]) -> tuple[str, str]:
    """Extrae nombres de centros poblados cercanos para español y quechua."""
    places = alert_data.get("exposure", {}).get("places") or []
    if not places:
        factors = alert_data.get("factors", {})
        places = factors.get("places") or []
    if isinstance(places, list) and places:
        primary = str(places[0])
        top3 = [str(p) for p in places[:3]]
        return ", ".join(top3), primary
    return "Huanta y La Mar", "Huanta"


def generate_radio_script(alert_data: dict[str, Any], aoi_id: str = "ayacucho-huanta") -> dict[str, Any]:
    """Genera el guion radial de 30–60 s en español y quechua chanka para una alerta."""
    b_cfg = load_bulletin_config()
    disclaimers = b_cfg.get("disclaimers", {})
    mandatory_notice = disclaimers.get(
        "mandatory_monitor",
        "Aviso de monitoreo. No reemplaza a INDECI ni a la autoridad local. Verificar en campo.",
    )
    quechua_mandatory = disclaimers.get(
        "quechua_mandatory_monitor",
        "Kayqa qawapayana willakuymi. Manam INDECIpa tukri willakuyninchu. Kikin allpapim qawakunan.",
    )

    alert_id = alert_data.get("alert_id") or alert_data.get("id", "alr_001")
    area_ha = float(alert_data.get("area_ha") or alert_data.get("metrics", {}).get("area_ha") or 1.0)
    risk_info = alert_data.get("risk") or {}
    risk_name = risk_info.get("dominant_risk_name") or alert_data.get("level", "Riesgo moderado")
    level = alert_data.get("level", "medio").lower()
    factors = alert_data.get("factors") or {}
    slope_deg = float(factors.get("slope_deg") or 14.0)
    crop_ha = float(factors.get("crop_ha") or factors.get("cropland_ha") or 0.0)

    recipe = alert_data.get("recipe") or {}
    recipe_name = recipe.get("risk_name") or "Receta natural de conservación"
    species = recipe.get("species_primary") or ["Queñua", "Colle", "Molle", "Ichu"]
    species_str = ", ".join(species[:3]) if isinstance(species, list) else "especies nativas"

    places_top3, primary_place = _get_places_str(alert_data)

    # Guion en español (estilo radioemisora comunitaria andina)
    script_es = (
        f"Atención, comunidades de Huanta y La Mar. GAIA Voz informa: "
        f"El radar satelital NISAR detectó cambios de cobertura en {area_ha:.1f} hectáreas "
        f"en el sector de {places_top3}. "
        f"Diagnóstico técnico: {risk_name}, en laderas de {slope_deg:.0f} grados con {crop_ha:.1f} "
        f"hectáreas de cultivo próximas. "
        f"Se recomienda aplicar la receta natural: {recipe_name}, priorizando {species_str} "
        f"y zanjas de infiltración. "
        f"Llamado a faena comunal minka con las autoridades de {primary_place}. "
        f"{mandatory_notice}"
    )

    # Guion en quechua chanka (revisado, regla 6: con aviso de validación continua)
    script_qu = (
        f"Allillanchu ayllukuna, Huantawan La Mar llaqtamasikuna. GAIA Voz willakuytam apamun: "
        f"NISAR radar satélitemi allpapi tikrakuykunata rikurun {area_ha:.1f} hectáreas tupupi "
        f"kay {places_top3} suyukunapi. "
        f"Chakrakunapa hichpanpim kachkan, urqu kinraykunapi. "
        f"Aylluntin minkapi llankaspa allpata sayachisun: {species_str} tarpuspa, "
        f"yaku purinan zanjakunata allaspa. "
        f"Umalliqkuna, kikin allpapi qawaykuychik. "
        f"{quechua_mandatory}"
    )

    words_es = len(script_es.split())
    words_qu = len(script_qu.split())
    duration_es_s = max(25, min(75, int(words_es / 130 * 60)))
    duration_qu_s = max(25, min(75, int(words_qu / 115 * 60)))

    stations = b_cfg.get("stations", [])

    return {
        "alert_id": alert_id,
        "aoi_id": aoi_id,
        "headline": f"Boletín radial: Alerta {level.upper()} en {primary_place}",
        "script_es": script_es,
        "script_qu": script_qu,
        "duration_es_seconds": duration_es_s,
        "duration_qu_seconds": duration_qu_s,
        "words_count_es": words_es,
        "words_count_qu": words_qu,
        "primary_place": primary_place,
        "nearby_places": places_top3,
        "stations": stations,
        "quechua_metadata": {
            "variant": "Quechua Chanka (Ayacucho)",
            "review_status": "revisado_chanka_borrador",
            "disclaimer": "Traducción en quechua chanka. Sujeta a validación comunitaria continua en campo.",
        },
        "disclaimer_mandatory": mandatory_notice,
    }


def generate_minka_call(alert_data: dict[str, Any], aoi_id: str = "ayacucho-huanta") -> dict[str, Any]:
    """Genera la convocatoria a Minka Digital para WhatsApp, SMS o asamblea comunal."""
    m_cfg = load_minka_config()
    defaults = m_cfg.get("minka", {}).get("defaults_by_intervention", {})
    alert_id = alert_data.get("alert_id") or alert_data.get("id", "alr_001")
    area_ha = float(alert_data.get("area_ha") or alert_data.get("metrics", {}).get("area_ha") or 1.0)
    level = alert_data.get("level", "medio").lower()

    places_top3, primary_place = _get_places_str(alert_data)

    recipe = alert_data.get("recipe") or {}
    interventions = recipe.get("interventions") or []
    int_id = interventions[0].get("intervention_id") if interventions else "zanjas_infiltracion"

    int_cfg = defaults.get(int_id, defaults.get("zanjas_infiltracion", {}))
    workers_per_ha = int(int_cfg.get("workers_per_ha", 25))
    total_workers = max(15, min(80, int(math.ceil(workers_per_ha * max(0.5, min(area_ha, 3.0))))))
    days_est = int(int_cfg.get("days_estimated", 3))

    tools = int_cfg.get("recommended_tools", ["Picos", "Palas", "Barretas", "Nivel en A"])
    supplies = int_cfg.get("supplies", ["Plantones nativos y piedras locales"])
    traditional_support = int_cfg.get("traditional_support", "Olla común con el comité de regantes")

    cost_data = alert_data.get("cost_benefit") or {}
    minka_savings = cost_data.get("minka_savings_soles")
    if not minka_savings:
        cost_total = alert_data.get("costs", {}).get("cost_total_soles") or 4500.0
        minka_savings = round(cost_total * 0.40, 2)

    recipe_title = recipe.get("risk_name") or "Restauración de ladera"

    wa_text = (
        f"🌿 *CONVOCATORIA MINKA COMUNAL - GAIA ALERTA* 🌿\n\n"
        f"📍 *Sector:* {primary_place} ({places_top3})\n"
        f"🛰️ *Detección radar NISAR:* {area_ha:.1f} ha con riesgo {level.upper()}\n"
        f"🌱 *Solución natural:* {recipe_title}\n"
        f"👥 *Meta comunal:* {total_workers} comuneros durante {days_est} días\n"
        f"🛠️ *Herramientas:* {', '.join(tools[:3])}\n"
        f"🍲 *Apoyo:* {traditional_support}\n"
        f"💰 *Ahorro comunal estimado:* S/ {minka_savings:,.0f} (hasta 40% del costo total)\n\n"
        f"🔗 *Evidencia satelital:* http://localhost:5173\n"
        f"⚠️ *Aviso de monitoreo. No reemplaza a INDECI. Verificar en campo.*"
    )
    wa_url = f"https://wa.me/?text={urllib.parse.quote(wa_text)}"

    # SMS compacto de verificación (Fase 4.2)
    sms_text = (
        f"GAIA Alerta ({alert_id[-8:]}): Cambio radar en {primary_place}. "
        f"¿Viste fuego o derrumbe? Responde 1 para SI, 2 para NO. "
        f"Aviso de monitoreo. Verificar en campo."
    )
    if len(sms_text) > 160:
        sms_text = sms_text[:157] + "..."

    return {
        "alert_id": alert_id,
        "aoi_id": aoi_id,
        "title": f"Faena Comunal Minka en {primary_place}",
        "primary_place": primary_place,
        "target_communities": places_top3.split(", ") if places_top3 else [primary_place],
        "needed_workers": total_workers,
        "estimated_days": days_est,
        "recommended_tools": tools,
        "supplies": supplies,
        "traditional_support": traditional_support,
        "savings_estimated_soles": minka_savings,
        "whatsapp": {
            "text": wa_text,
            "url": wa_url,
        },
        "sms_verification": {
            "text": sms_text,
            "char_count": len(sms_text),
            "mode": "preview_only",
            "notice": (
                "Modo vista previa: ningún SMS enviado sin credencial Twilio "
                "ni consentimiento explícito registrado."
            ),
        },
    }


def synthesize_bulletin_audio_wav(
    text: str, cache_path: Path | None = None, sample_rate: int = 22050
) -> bytes:
    """Sintetiza audio WAV en el servidor usando SAPI (Windows) o generador WAV puro."""
    if cache_path and cache_path.is_file() and cache_path.stat().st_size > 1000:
        return cache_path.read_bytes()

    # Intento 1: Windows SAPI vía PowerShell (sin dependencias externas en Windows)
    if os.name == "nt":
        tmp_dir = tempfile.gettempdir()
        tmp_ps1 = Path(tmp_dir) / f"sapi_{os.getpid()}_{int(tempfile.tempnam() if False else 1)}.ps1"
        tmp_txt = Path(tmp_dir) / f"sapi_txt_{os.getpid()}.txt"
        tmp_wav = Path(tmp_dir) / f"sapi_out_{os.getpid()}.wav"

        ps_script = (
            "param([string]$TxtPath, [string]$OutPath)\n"
            "Add-Type -AssemblyName System.Speech\n"
            "$t = [System.IO.File]::ReadAllText($TxtPath, [System.Text.Encoding]::UTF8)\n"
            "$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
            "$voice.SetOutputToWaveFile($OutPath)\n"
            "$voice.Speak($t)\n"
            "$voice.Dispose()\n"
        )
        try:
            tmp_txt.write_text(text, encoding="utf-8")
            tmp_ps1.write_text(ps_script, encoding="utf-8")
            res = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(tmp_ps1),
                    "-TxtPath",
                    str(tmp_txt),
                    "-OutPath",
                    str(tmp_wav),
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if res.returncode == 0 and tmp_wav.is_file() and tmp_wav.stat().st_size > 1000:
                wav_bytes = tmp_wav.read_bytes()
                if cache_path:
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    cache_path.write_bytes(wav_bytes)
                return wav_bytes
        except Exception as exc:
            logger.warning("Fallo en síntesis SAPI: %s. Usando generador WAV acústico.", exc)
        finally:
            tmp_ps1.unlink(missing_ok=True)
            tmp_txt.unlink(missing_ok=True)
            tmp_wav.unlink(missing_ok=True)

    # Intento 2: Generador acústico de señal radial WAV en Python puro (16-bit PCM, sonido de aviso)
    # Crea un tono armónico andino (pentatónico / campana de aviso) de 4 segundos
    duration = 4.0
    num_samples = int(duration * sample_rate)
    notes = [440.0, 523.25, 659.25, 783.99]  # La - Do - Mi - Sol (acorde andino)

    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        # Envelope de campana suave
        env = math.exp(-1.5 * (t % 1.0)) * min(1.0, t * 10.0)
        chord_idx = min(len(notes) - 1, int(t))
        freq = notes[chord_idx]
        val = 0.4 * math.sin(2.0 * math.pi * freq * t) + 0.2 * math.sin(4.0 * math.pi * freq * t)
        sample = int(max(-32767, min(32767, val * env * 24000)))
        frames.extend(struct.pack("<h", sample))

    import io

    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    wav_bytes = bio.getvalue()
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(wav_bytes)
    return wav_bytes


# ---------------------------------------------------------------------------
# Gestión de compromisos comunitarios para la Minka
# ---------------------------------------------------------------------------


def get_commitments(aoi_id: str, zone_id: str) -> list[dict[str, Any]]:
    """Lee la lista de compromisos comunitarios registrados para una mancha."""
    if not COMMITMENTS_FILE.is_file():
        return []
    try:
        data = json.loads(COMMITMENTS_FILE.read_text(encoding="utf-8"))
        zone_key = f"{aoi_id}:{zone_id}"
        return data.get(zone_key, [])
    except Exception:
        return []


def add_commitment(
    aoi_id: str,
    zone_id: str,
    community: str,
    volunteers: int,
    tools: str,
    contact_name: str = "",
) -> dict[str, Any]:
    """Registra un nuevo compromiso comunitario para una faena minka."""
    from datetime import datetime

    COMMITMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    store: dict[str, list[dict[str, Any]]] = {}
    if COMMITMENTS_FILE.is_file():
        try:
            store = json.loads(COMMITMENTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            store = {}

    zone_key = f"{aoi_id}:{zone_id}"
    commitments = store.get(zone_key, [])

    new_item = {
        "id": f"com_{len(commitments) + 1}",
        "timestamp": datetime.now(UTC).isoformat(),
        "community": community.strip() or "Comunidad local",
        "volunteers": max(1, min(100, int(volunteers))),
        "tools": tools.strip() or "Herramientas de labranza",
        "contact_name": contact_name.strip() or "Autoridad comunal",
    }
    commitments.append(new_item)
    store[zone_key] = commitments
    COMMITMENTS_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    return new_item
