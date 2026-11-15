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
    nearby = alert_data.get("nearby_places") or (alert_data.get("exposure") or {}).get("nearby_places") or []
    places = sorted((p for p in nearby if p.get("name") and p.get("distance_m") is not None
                     and p["distance_m"] >= 0), key=lambda p: p["distance_m"])[:3]
    names = [p["name"] for p in places]
    return (", ".join(names), names[0]) if names else ("", "")


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
    area_ha = alert_data.get("area_ha") or alert_data.get("metrics", {}).get("area_ha")
    if not area_ha:
        raise ValueError("La mancha no tiene área medida: no se genera boletín")
    area_ha = float(area_ha)
    risk_name = alert_data.get("risk_name") or "causa por verificar"
    level = str(alert_data.get("level", "")).lower()
    factors = alert_data.get("factors") or {}
    slope_deg = factors.get("slope_deg")
    crop_ha = factors.get("crop_ha") or factors.get("cropland_ha")

    recipe = alert_data.get("recipe") or {}
    species = recipe.get("species_primary") or []
    species_str = ", ".join(species[:3])

    places_top3, primary_place = _get_places_str(alert_data)
    where = f"cerca de {places_top3}" if places_top3 else "en el área satelital analizada"

    # Guion en español: solo frases respaldadas por datos de la mancha
    parts = [
        "Atención, comunidades. GAIA Voz informa:",
        f"el radar NISAR detectó cambios en {area_ha:.1f} hectáreas {where}.",
    ]
    if slope_deg is not None:
        parts.append(f"La ladera tiene una pendiente media de {slope_deg:.0f} grados.")
    if crop_ha:
        parts.append(f"Hay {float(crop_ha):.1f} hectáreas de cultivo dentro de la zona.")
    if recipe:
        parts.append(f"Posible situación: {risk_name}.")
        if species_str:
            parts.append(f"Si en campo se confirma, se recomienda sembrar {species_str}.")
    else:
        parts.append("La causa aún no se conoce. Autoridades: verificar en campo.")
    parts.append(mandatory_notice)
    script_es = " ".join(parts)

    # Quechua: solo se usa cuando un hablante lo revisó (config/nbs/bulletin.yaml)
    q_cfg = b_cfg.get("quechua", {})
    reviewed = q_cfg.get("review_status") == "revisado"
    script_qu = (
        "Allillanchu ayllukuna, Huantawan La Mar llaqtamasikuna. GAIA Voz willakuytam apamun: "
        f"NISAR radar satélitemi allpapi tikrakuykunata rikurun {area_ha:.1f} hectáreas tupupi. "
        "Umalliqkuna, kikin allpapi qawaykuychik. "
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
        "headline": f"Boletín radial: monitoreo {level.upper()}"
                    + (f" cerca de {primary_place}" if primary_place else ""),
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
            "variant": q_cfg.get("variant", "Quechua Chanka (Ayacucho)"),
            "review_status": q_cfg.get("review_status", "pendiente"),
            "reviewed": reviewed,
            "disclaimer": q_cfg.get("disclaimer", "Borrador sin revisar por un hablante. No difundir."),
        },
        "disclaimer_mandatory": mandatory_notice,
    }


def generate_minka_call(alert_data: dict[str, Any], aoi_id: str = "ayacucho-huanta") -> dict[str, Any]:
    """Genera la convocatoria a Minka Digital para WhatsApp, SMS o asamblea comunal."""
    m_cfg = load_minka_config()
    defaults = m_cfg.get("minka", {}).get("defaults_by_intervention", {})
    alert_id = alert_data.get("alert_id") or alert_data.get("id", "")
    places_top3, primary_place = _get_places_str(alert_data)
    techniques = [{"name": b["name"], "timing": b.get("timing")}
                  for b in alert_data.get("budget", []) if b.get("name")]
    tools = list(dict.fromkeys(tool for b in alert_data.get("budget", [])
                 for tool in defaults.get(b.get("intervention_id"), {}).get("recommended_tools", [])))
    area = alert_data.get("area_ha")
    lines = ["PROPUESTA MINKA COMUNAL - GAIA", f"Zona satelital: {alert_id}"]
    if primary_place:
        lines.append(f"Poblados cercanos: {places_top3}")
    if area is not None:
        lines.append(f"Area de cambio radar: {area:.2f} ha")
    for technique in techniques:
        lines.append(f"Tecnica sugerida: {technique['name']}" +
                     (f". Temporada: {technique['timing']}" if technique.get("timing") else ""))
    if tools:
        lines.append("Herramientas sugeridas: " + ", ".join(tools))
    notice = "Aviso de monitoreo. No reemplaza a INDECI ni a la autoridad local. Verificar en campo."
    lines.append(notice)
    text = "\n".join(lines)
    sms = None
    if primary_place:
        sms_text = f"GAIA Alerta: cambio radar cerca de {primary_place}. {notice}"
        sms = {"text": sms_text, "char_count": len(sms_text), "mode": "preview_only",
               "notice": "Vista previa. No se ha enviado ningun SMS."}
    return {
        "alert_id": alert_id, "aoi_id": aoi_id,
        "title": "Propuesta de Minka comunal", "primary_place": primary_place,
        "target_communities": places_top3.split(", ") if places_top3 else [],
        "techniques": techniques, "needed_workers": None, "estimated_days": None,
        "savings_estimated_soles": None, "recommended_tools": tools,
        "supplies": [], "traditional_support": "",
        "whatsapp": {"text": text, "url": f"https://wa.me/?text={urllib.parse.quote(text)}"},
        "sms_verification": sms,
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
