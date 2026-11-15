"""Read-only local photo catalogue and georeferenced imagery endpoints."""

from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from shapely.geometry import shape

from sarlab_pipeline.photos import relation, zone_distance_km

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


def field_image(filename: str) -> Path | None:
    if os.getenv("GAIA_COMMERCIAL") == "1" or not re.fullmatch(r"[a-z0-9-]{1,100}\.(?:jpeg|png)", filename):
        return None
    root = published() / "field-photos" / "images"
    path = root / filename
    return path if path.resolve().is_relative_to(root.resolve()) and path.is_file() else None


@router.get("/api/field-photos/images/{filename}")
def field_photo_file(filename: str):
    path = field_image(filename)
    if path is None:
        raise HTTPException(404, "Foto de informe no publicada")
    return FileResponse(path, headers={"Cache-Control": "no-cache"})


@router.get("/api/field-dem/{aoi}/{part}")
def field_elevation(aoi: str, part: Literal["metadata", "grid"]):
    if not re.fullmatch(r"[a-z0-9-]{1,80}", aoi):
        raise HTTPException(404, "Relieve no publicado")
    root = published() / "field-dem"
    path = root / f"{aoi}.{'json' if part == 'metadata' else 'bin'}"
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise HTTPException(404, "Relieve no publicado")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})


@router.get("/api/field-aerial/{aoi}/{filename}")
def field_aerial_file(aoi: str, filename: str):
    if not re.fullmatch(r"[a-z0-9-]{1,80}", aoi) or not re.fullmatch(r"\d+-\d+\.(?:jpg|png)", filename):
        raise HTTPException(404, "Imagen Sentinel-2 no publicada")
    root = published() / "field-aerial" / aoi
    path = root / filename
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise HTTPException(404, "Imagen Sentinel-2 no publicada")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})


def field_catalog(aoi: str, geometry: dict) -> tuple[list[dict], list[dict]]:
    photos, references = [], {}
    for item in read(published() / "field-photos" / f"{aoi}.json", []):
        if not field_image(item["image_url"].rsplit("/", 1)[-1]):
            continue
        if item["lon"] is None or item["lat"] is None:
            references[item["source_url"]] = {
                key: item[key] for key in ("source_url", "page", "place", "author", "taken_at")
            }
            continue
        distance = zone_distance_km(geometry, item["lon"], item["lat"])
        if distance < 10:
            photos.append({
                **item, "distance_km": distance,
                "location_label": f"{distance:.1f} km · ubicación aproximada de la comunidad",
            })
    return sorted(photos, key=lambda item: item["distance_km"]), list(references.values())


def citizen_photos(geometry: dict) -> list[dict]:
    from . import reports
    from .main import _reports_db

    photos = []
    for report in reports.list_reports(_reports_db(), "visible"):
        photo = report.get("photo")
        if not photo:
            continue
        distance = zone_distance_km(geometry, report["lon"], report["lat"])
        if distance <= 5:
            photos.append({
                **photo, "id": report["id"], "title": "Foto aportada por la comunidad",
                "source_url": photo["image_url"], "thumbnail_url": photo["image_url"],
                "taken_at": report["observed_at"][:10], "lon": report["lon"], "lat": report["lat"],
                "distance_km": distance, "location_label": f"{distance:.1f} km · ubicación redondeada",
                "role": "citizen",
                "modifications": "Reporte comunitario · imagen redimensionada sin metadatos.",
            })
    return sorted(photos, key=lambda item: item["distance_km"])


def nearby_settlements(aoi: str, geometry: dict) -> list[dict]:
    data = read(published() / "community" / f"{aoi}.json", {})
    west, south, east, north = shape(geometry).bounds
    places = []
    for item in data.get("places", []):
        if item.get("kind") != "place" or not item.get("center"):
            continue
        lon, lat = item["center"]
        if not (west - .04 <= lon <= east + .04 and south - .04 <= lat <= north + .04):
            continue
        distance = zone_distance_km(geometry, lon, lat)
        if distance <= 3:
            places.append({"name": item["name"], "center": item["center"], "distance_km": distance})
    return sorted(places, key=lambda item: item["distance_km"])[:4]


@router.get("/api/remediation/{aoi}/{zone_id}/street-view")
def street_view(aoi: str, zone_id: str):
    zone = zone_record(aoi, zone_id)
    key = os.getenv("GOOGLE_MAPS_KEY")
    if not key:
        return None
    point = shape(zone["geometry"]).representative_point()
    try:
        response = httpx.get(
            "https://maps.googleapis.com/maps/api/streetview/metadata",
            params={"key": key, "location": f"{point.y},{point.x}", "radius": 2000, "source": "outdoor"},
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") == "ZERO_RESULTS":
            return None
        if payload.get("status") != "OK":
            raise HTTPException(503, "Street View no está disponible.")
        date, pano = payload.get("date", ""), payload["pano_id"]
        lon, lat = float(payload["location"]["lng"]), float(payload["location"]["lat"])
        if not math.isfinite(lon) or not math.isfinite(lat) or not re.fullmatch(r"\d{4}(?:-\d{2})?", date):
            return None
        distance = zone_distance_km(zone["geometry"], lon, lat)
        if distance >= 2:
            return None
        url = "https://www.google.com/maps/@?" + urlencode({"api": 1, "map_action": "pano", "pano": pano})
        return JSONResponse(
            {"url": url, "date": date, "distance_km": round(distance, 2)},
            headers={"Cache-Control": "no-store"},
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        raise HTTPException(503, "No se pudo consultar Street View.") from None


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
    community_reports = citizen_photos(zone["geometry"])
    field_photos, field_references = field_catalog(aoi, zone["geometry"])
    future_climate = read(published() / "climate-future" / f"{aoi}.json")
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
        "community_reports": community_reports,
        "nearby_settlements": nearby_settlements(aoi, zone["geometry"]),
        "field_photos": field_photos,
        "field_references": field_references,
        "future_climate": future_climate,
        "greenness": read(published() / "greenness" / f"{aoi}.json"),
        "field_aerial": read(published() / "field-aerial" / aoi / "catalog.json"),
        "street_view_enabled": bool(os.getenv("GOOGLE_MAPS_KEY")),
        "soil": soil,
        "soil_photo": photo(soil_reference.get("photo_id")),
        "techniques": techniques,
        "imagery": imagery,
        "warnings": data.get("warnings", []),
        "pins": [
            p for p in field_photos + community_reports + nearby + community_photos
            if p.get("lat") is not None and p.get("lon") is not None
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
