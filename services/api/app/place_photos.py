"""Read-only local photo catalogue and georeferenced imagery endpoints."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from sarlab_pipeline.photos import relation

router = APIRouter()


def published() -> Path:
    from .main import PROCESSED

    return PROCESSED.parent / "04_published"


def read(path: Path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def zone_record(aoi: str, zone_id: str) -> dict:
    if not re.fullmatch(r"[a-z0-9-]{1,80}", aoi) or not re.fullmatch(r"[A-Za-z0-9_-]{1,180}", zone_id):
        raise HTTPException(422, "Identificador inválido")
    data = read(published() / "remediation" / f"{aoi}.json", {})
    zone = next((item for item in data.get("alerts", []) if item["alert_id"] == zone_id), None)
    if not zone:
        raise HTTPException(404, "Mancha no encontrada en la publicación de este territorio")
    return zone


@router.get("/api/photos/images/{filename}")
def photo_file(filename: str):
    if not re.fullmatch(r"[a-z0-9-]{1,100}(?:-thumb)?\.jpg", filename):
        raise HTTPException(404, "Foto no encontrada")
    root = published() / "photos" / "images"
    target = root / filename
    if not target.resolve().is_relative_to(root.resolve()) or not target.is_file():
        raise HTTPException(404, "Foto no publicada")
    return FileResponse(target, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/api/remediation/{aoi}/{zone_id}/place")
def place_catalog(aoi: str, zone_id: str):
    zone = zone_record(aoi, zone_id)
    data = read(published() / "photos" / f"{aoi}.json", {})
    photo_index = data.get("photos", {})
    zone_photos = data.get("zones", {}).get(zone_id, {})

    def photo(pid):
        if not isinstance(pid, str) or not re.fullmatch(r"[a-z0-9-]{1,100}", pid):
            return None
        item = photo_index.get(pid)
        if not item or not all(
            item.get(k) for k in ("author", "taken_at", "license", "license_url", "source_url")
        ):
            return None
        if not (published() / "photos" / "images" / f"{pid}.jpg").is_file():
            return None
        return {**item, **relation(zone["geometry"], item)}

    species_names = set()
    for name in (zone.get("recipe") or {}).get("species_primary", []):
        match = re.search(r"\((.+)\)", name)
        if match:
            species_names.add(match.group(1))
    species_names.update(s["scientific"] for s in (zone.get("soil") or {}).get("species", []))
    species = [
        {**s, "photo": photo(s.get("photo_id"))}
        for s in data.get("species", [])
        if s["scientific"] in species_names
    ]
    nearby = [p for pid in zone_photos.get("nearby", []) if (p := photo(pid)) and p["distance_km"] <= 5]
    community = data.get("communities", {}).get(zone_photos.get("community_id"))
    community_photos = [p for pid in (community or {}).get("photo_ids", []) if (p := photo(pid))]
    intervention_ids = {b["intervention_id"] for b in zone.get("budget", [])}
    techniques = [
        {**t, "photos": [p for pid in t.get("photo_ids", []) if (p := photo(pid))]}
        for t in data.get("techniques", [])
        if t["id"] in intervention_ids
    ]
    soil = zone.get("soil")
    soil_reference = next((s for s in data.get("soils", []) if s["name"] == (soil or {}).get("wrb_name")), {})
    imagery = read(published() / "place-imagery" / aoi / "catalog.json", {}).get("zones", {}).get(zone_id, {})
    return {
        "aoi_id": aoi,
        "zone_id": zone_id,
        "available": bool(data),
        "generated_at": data.get("generated_at"),
        "species": species,
        "nearby": nearby,
        "community": community,
        "community_photos": community_photos,
        "soil": soil,
        "soil_photo": photo(soil_reference.get("photo_id")),
        "techniques": techniques,
        "imagery": imagery,
        "warnings": data.get("warnings", []),
        "pins": [
            p for p in nearby + community_photos if p.get("lat") is not None and p.get("lon") is not None
        ],
    }


@router.get("/api/remediation/{aoi}/{zone_id}/imagery/{moment}.png")
def imagery_file(aoi: str, zone_id: str, moment: Literal["past", "before", "after"]):
    zone_record(aoi, zone_id)
    root = published() / "place-imagery" / aoi
    metadata = read(root / "catalog.json", {}).get("zones", {}).get(zone_id, {}).get(moment, {})
    path = root / zone_id / f"{moment}.png"
    if (
        not metadata.get("available")
        or not path.resolve().is_relative_to(root.resolve())
        or not path.is_file()
    ):
        raise HTTPException(404, metadata.get("reason", "Recorte georreferenciado sin publicar"))
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
