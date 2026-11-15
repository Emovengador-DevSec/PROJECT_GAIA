"""Licensed, locally cached reference photographs and per-zone geographic evidence."""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
import time
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import httpx
import yaml
from PIL import Image, ImageOps
from pyproj import CRS, Transformer
from shapely import transform
from shapely.geometry import Point, shape

from .settings import CONFIG_DIR, PUBLISHED

COMMONS = "https://commons.wikimedia.org/w/api.php"
INAT = "https://api.inaturalist.org/v1/observations"
PERU_PLACE_ID = 7513  # iNaturalist place "Peru"
USER_AGENT = "GAIA-PhotoCollector/1.0 (educational geographic evidence collector)"
LICENSES = {
    "cc-by": "https://creativecommons.org/licenses/by/4.0/",
    "cc-by-sa": "https://creativecommons.org/licenses/by-sa/4.0/",
    "cc0": "https://creativecommons.org/publicdomain/zero/1.0/",
}
IMAGE_HOSTS = {
    "api.openverse.org",
    "wrb.isric.org",
    "upload.wikimedia.org",
    "thumb.wikimedia.org",
    "static.inaturalist.org",
    "inaturalist-open-data.s3.amazonaws.com",
}
MAX_IMAGE_BYTES = 15_000_000


def plain(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", value or "")).split())


def photo_license(code: str, url: str = "") -> tuple[str, str] | None:
    code = code.lower().strip().replace(" ", "-")
    if code == "cc0-1.0":
        code = "cc0"
    if code in LICENSES:
        return code.upper(), LICENSES[code]
    if re.fullmatch(r"cc-by(-sa)?-\d\.\d", code):
        version = code[-3:]
        kind = "by-sa" if "-sa-" in code else "by"
        expected = f"https://creativecommons.org/licenses/{kind}/{version}/"
        if url.rstrip("/").replace("http://", "https://") == expected.rstrip("/"):
            return code.upper(), expected
    return None


def zone_distance_km(geometry: dict, lon: float, lat: float) -> float:
    """Distance to the actual polygon boundary, not its centroid (local metric CRS)."""
    polygon = shape(geometry)
    center = polygon.centroid
    local = CRS.from_proj4(f"+proj=aeqd +lat_0={center.y} +lon_0={center.x} +datum=WGS84 +units=m")
    project = Transformer.from_crs(4326, local, always_xy=True).transform
    return (
        transform(polygon, project, interleaved=False).distance(
            transform(Point(lon, lat), project, interleaved=False)
        )
        / 1000
    )


def relation(geometry: dict, photo: dict) -> dict:
    if photo.get("role") in ("species", "soil", "technique"):
        return {
            "distance_km": None,
            "location_label": "Ejemplo en otro lugar · " + photo.get("place", "ubicación no publicada"),
        }
    lon, lat = photo.get("lon"), photo.get("lat")
    if lon is None or lat is None:
        return {"distance_km": None, "location_label": "Ubicación sin verificar"}
    distance = zone_distance_km(geometry, lon, lat)
    accuracy = photo.get("accuracy_m")
    # Include the uncertainty bound when claiming proximity to a zone.
    nearby = accuracy is not None and distance + accuracy / 1000 < 0.5
    return {
        "distance_km": round(distance, 3),
        "location_label": "Esta zona (< 500 m)"
        if nearby
        else f"A {distance:.2f} km de la zona".replace(".", ","),
    }


def inat_photo(observation: dict, role: str) -> dict | None:
    if (
        observation.get("quality_grade") != "research"
        or observation.get("taxon", {}).get("iconic_taxon_name") != "Plantae"
    ):
        return None
    if (
        observation.get("obscured")
        or observation.get("geoprivacy") not in (None, "open")
        or observation.get("taxon_geoprivacy") not in (None, "open")
    ):
        return None
    coordinates = (observation.get("geojson") or {}).get("coordinates")
    if coordinates and (
        len(coordinates) != 2
        or not all(isinstance(c, (int, float)) and math.isfinite(c) for c in coordinates)
        or not -180 <= coordinates[0] <= 180
        or not -90 <= coordinates[1] <= 90
    ):
        return None
    observed = observation.get("observed_on")
    user = observation.get("user") or {}
    author = user.get("name") or user.get("login")
    taxon = observation.get("taxon") or {}
    coordinates = (observation.get("geojson") or {}).get("coordinates")
    if not observed or not author:
        return None
    if role == "nearby" and (
        not coordinates
        or observation.get("positional_accuracy") is None
        or observation["positional_accuracy"] > 100
    ):
        return None
    for item in observation.get("photos", []):
        license_info = photo_license(item.get("license_code") or "")
        if not license_info or item.get("hidden") or item.get("flags"):
            continue
        return {
            "id": f"inat-{item['id']}",
            "title": taxon.get("preferred_common_name") or taxon.get("name"),
            "scientific": taxon.get("name"),
            "author": plain(item.get("attribution"))
            if item.get("attribution") and item["attribution"] != "no rights reserved"
            else plain(author),
            "author_role": "Crédito de la foto"
            if item.get("attribution") and item["attribution"] != "no rights reserved"
            else "Usuario de la observación",
            "license": license_info[0],
            "license_url": license_info[1],
            "source_url": f"https://www.inaturalist.org/observations/{observation['id']}",
            "taken_at": observed,
            "lat": coordinates[1] if coordinates else None,
            "lon": coordinates[0] if coordinates else None,
            "accuracy_m": observation.get("positional_accuracy"),
            "role": role,
            "place": plain(observation.get("place_guess") or "Ubicación no publicada"),
            "remote_url": item["url"].replace("/square.", "/large."),
            "distance_km": None,
        }
    return None


def commons_photo(page: dict, role: str) -> dict | None:
    info = (page.get("imageinfo") or [{}])[0]
    metadata = info.get("extmetadata") or {}

    def field(key):
        return plain(metadata.get(key, {}).get("value", ""))

    license_info = photo_license(field("LicenseShortName"), field("LicenseUrl"))
    author, taken = field("Artist"), field("DateTimeOriginal")
    if (
        not license_info
        or not author
        or not taken
        or info.get("mime") not in ("image/jpeg", "image/png", "image/webp")
    ):
        return None
    coordinates = (page.get("coordinates") or [{}])[0]
    return {
        "id": f"commons-{page['pageid']}",
        "title": page.get("title", "Foto").removeprefix("File:"),
        "author": author,
        "license": license_info[0],
        "license_url": license_info[1],
        "source_url": info.get("descriptionurl"),
        "taken_at": taken,
        "lat": coordinates.get("lat"),
        "lon": coordinates.get("lon"),
        "accuracy_m": None,
        "role": role,
        "place": field("Location") or "Ubicación de referencia; consulta la fuente",
        "description": field("ImageDescription")[:500],
        "distance_km": None,
        "remote_url": info.get("thumburl") or info.get("url"),
    }


class Collector:
    def __init__(self, output: Path, client: httpx.Client, refresh: bool = False):
        self.output, self.client, self.refresh = output, client, refresh
        self.cache = output / "cache"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.last_request = 0.0
        self.disabled: set[str] = set()
        self.errors: list[str] = []

    def get_json(self, url: str, params: dict) -> dict:
        key = hashlib.sha256((url + json.dumps(params, sort_keys=True)).encode()).hexdigest()
        path = self.cache / f"{key}.json"
        if path.is_file() and not self.refresh:
            return json.loads(path.read_text(encoding="utf-8"))
        host = urlparse(url).hostname or ""
        if host in self.disabled:
            return {}
        time.sleep(max(0, 1.2 - (time.monotonic() - self.last_request)))
        for attempt in range(3):
            try:
                self.last_request = time.monotonic()
                response = self.client.get(url, params=params)
                if response.status_code == 429 or response.status_code == 503:
                    retry = response.headers.get("Retry-After", "5")
                    time.sleep(min(30, float(retry) if retry.isdigit() else 5) * (attempt + 1))
                    continue
                response.raise_for_status()
                value = response.json()
                if value.get("error"):
                    raise ValueError("Remote API returned an error")
                path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
                return value
            except (httpx.HTTPError, ValueError):
                self.errors.append(f"{host}: respuesta no disponible; se conserva un estado vacío")
                self.disabled.add(host)
                return {}
        self.errors.append(f"{host}: límite remoto; reintenta más tarde")
        self.disabled.add(host)
        return {}

    def store(self, photo: dict | None) -> dict | None:
        if not photo or not all(
            photo.get(k) for k in ("author", "taken_at", "license", "license_url", "source_url")
        ):
            return None
        if not photo_license(photo["license"], photo["license_url"]):
            return None
        if not re.fullmatch(
            r"(?:inat-\d+|commons-\d+|commons-curated-[a-f0-9]{12}|reference-[a-f0-9]{12})",
            photo.get("id", ""),
        ):
            return None
        source_url = urlparse(photo["source_url"])
        if source_url.scheme != "https" or source_url.hostname not in (
            "commons.wikimedia.org",
            "www.inaturalist.org",
            "www.flickr.com",
            "wrb.isric.org",
        ):
            return None
        url = photo.get("remote_url", "")
        if urlparse(url).scheme != "https" or urlparse(url).hostname not in IMAGE_HOSTS:
            return None
        target = self.output / "images" / f"{photo['id']}.jpg"
        target.parent.mkdir(exist_ok=True)
        if not target.is_file():
            try:
                with self.client.stream("GET", url, follow_redirects=False) as response:
                    response.raise_for_status()
                    if urlparse(str(response.url)).hostname not in IMAGE_HOSTS:
                        return None
                    chunks, total = [], 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > MAX_IMAGE_BYTES:
                            raise ValueError("Imagen demasiado grande")
                        chunks.append(chunk)
                with Image.open(BytesIO(b"".join(chunks))) as source:
                    if source.width * source.height > 40_000_000:
                        return None
                    image = ImageOps.exif_transpose(source).convert("RGB")
                    image.thumbnail((800, 800))
                    image.save(target, "JPEG", quality=88)
                    image.thumbnail((96, 96))
                    image.save(target.with_name(f"{photo['id']}-thumb.jpg"), "JPEG", quality=80)
            except (httpx.HTTPError, OSError, ValueError, Image.DecompressionBombError):
                self.errors.append(f"Imagen {photo['id']} no descargada")
                return None
        with Image.open(target) as stored_image:
            width, height = stored_image.size
        result = {k: v for k, v in photo.items() if k != "remote_url"}
        result.update(width=width, height=height)
        result.update(
            image_url=f"/api/photos/images/{photo['id']}.jpg",
            thumbnail_url=f"/api/photos/images/{photo['id']}-thumb.jpg",
            modifications="Redimensionada a un máximo de 800 px; miniatura de 96 px",
            retrieved_at=datetime.fromtimestamp(target.stat().st_mtime, UTC).isoformat(),
        )
        return result

    def commons(self, query: str = "", titles: list[str] | None = None, role: str = "species") -> list[dict]:
        params = {
            "action": "query",
            "format": "json",
            "prop": "imageinfo|coordinates",
            "iiprop": "url|extmetadata|mime",
            "iiurlwidth": 800,
            "colimit": "max",
        }
        if titles:
            params["titles"] = "|".join(titles)
        else:
            params.update(
                generator="search", gsrsearch=query + " filetype:bitmap", gsrnamespace=6, gsrlimit=6
            )
        pages = self.get_json(COMMONS, params).get("query", {}).get("pages", {})
        return [photo for page in pages.values() if (photo := commons_photo(page, role))]


def species_config() -> list[dict]:
    recipes = yaml.safe_load((CONFIG_DIR / "nbs/recipes.yaml").read_text(encoding="utf-8"))
    soils = yaml.safe_load((CONFIG_DIR / "nbs/soils.yaml").read_text(encoding="utf-8"))
    species = {}
    native_path = CONFIG_DIR / "nbs/native_species.yaml"
    if native_path.exists():
        for item in yaml.safe_load(native_path.read_text(encoding="utf-8")).get("species", []):
            species[item["scientific"]] = {**item, "function": item["benefit"]}
    for soil in soils["groups"]:
        for item in soil.get("species", []):
            species.setdefault(item["scientific"], dict(item))
    for recipe in recipes["recipes"]:
        for item in recipe.get("species_primary", []):
            match = re.fullmatch(r"(.+?)\s*\((.+)\)", item)
            if match:
                name, scientific = match.groups()
                species.setdefault(
                    scientific,
                    {
                        "name": name,
                        "scientific": scientific,
                        "function": "Especie incluida en la receta; confirmar su uso en campo",
                    },
                )
    return list(species.values())


def publish(aoi: str, *, refresh: bool = False) -> dict:
    if not re.fullmatch(r"[a-z0-9-]+", aoi):
        raise ValueError("Identificador de territorio inválido")
    remediation_path = PUBLISHED / "remediation" / f"{aoi}.json"
    if not remediation_path.is_file():
        raise ValueError("Primero publica las zonas con sarlab remediation --aoi " + aoi)
    remediation = json.loads(remediation_path.read_text(encoding="utf-8"))
    zones = remediation["alerts"]
    output = PUBLISHED / "photos"
    output.mkdir(parents=True, exist_ok=True)
    photos, species, communities = {}, [], {}
    community_path = PUBLISHED / "community" / f"{aoi}.json"
    places = (
        json.loads(community_path.read_text(encoding="utf-8")).get("places", [])
        if community_path.exists()
        else []
    )
    places_by_url = {p.get("url"): p for p in places if p.get("center")}
    with httpx.Client(timeout=35, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        collector = Collector(output, client, refresh)
        for item in species_config():
            name = item["scientific"].replace(" spp.", "").strip()
            taxa = collector.get_json("https://api.inaturalist.org/v1/taxa", {"q": name, "per_page": 10})
            taxon = next(
                (
                    t
                    for t in taxa.get("results", [])
                    if t.get("iconic_taxon_name") == "Plantae"
                    and name.casefold()
                    in {str(t.get("name", "")).casefold(), str(t.get("matched_term", "")).casefold()}
                ),
                None,
            )

            def inat(place: int | None, taxon: dict | None = taxon) -> list[dict]:
                if not taxon:
                    return []
                params = {"taxon_id": taxon["id"], "iconic_taxa": "Plantae", "quality_grade": "research",
                          "photo_license": "cc-by,cc-by-sa,cc0", "per_page": 12, "order_by": "votes"}
                if place:
                    params["place_id"] = place
                response = collector.get_json(INAT, params)
                return [
                    p
                    for o in response.get("results", [])
                    if (o.get("taxon", {}).get("id") == taxon["id"]
                        or taxon["id"] in o.get("taxon", {}).get("ancestor_ids", []))
                    and (p := inat_photo(o, "species"))
                ]

            # Peru first (people should recognise the plant), then Commons, then anywhere.
            candidates = inat(PERU_PLACE_ID) or collector.commons(name) or inat(None)
            if not candidates and " " in name:
                # No licensed photo of the species: fall back to its genus observed in Peru.
                genus = collector.get_json("https://api.inaturalist.org/v1/taxa",
                                           {"q": name.split()[0], "rank": "genus", "per_page": 5})
                genus_taxon = next((t for t in genus.get("results", [])
                                    if t.get("name") == name.split()[0]
                                    and t.get("iconic_taxon_name") == "Plantae"), None)
                candidates = inat(PERU_PLACE_ID, genus_taxon) if genus_taxon else []
            stored = next((p for candidate in candidates if (p := collector.store(candidate))), None)
            if stored:
                photos[stored["id"]] = stored
            species.append({**item, "photo_id": stored["id"] if stored else None})
        cells = {}
        for zone in zones:
            center = shape(zone["geometry"]).centroid
            key = (math.floor(center.x / 0.05), math.floor(center.y / 0.05))
            cells.setdefault(key, []).append(zone)
        cell_photos = {}
        for (x, y), members in cells.items():
            # 9 km covers a 0.05 degree cell plus the requested 5 km search radius.
            response = collector.get_json(
                INAT,
                {
                    "lat": (y + 0.5) * 0.05,
                    "lng": (x + 0.5) * 0.05,
                    "radius": 9,
                    "quality_grade": "research",
                    "photo_license": "cc-by,cc-by-sa,cc0",
                    "iconic_taxa": "Plantae",
                    "per_page": 100,
                    "order_by": "observed_on",
                },
            )
            unique = {}
            for observation in response.get("results", []):
                candidate = inat_photo(observation, "nearby")
                if not candidate or candidate["scientific"] in unique:
                    continue
                if not any(
                    zone_distance_km(z["geometry"], candidate["lon"], candidate["lat"]) <= 5 for z in members
                ):
                    continue
                stored = collector.store(candidate)
                if stored:
                    photos[stored["id"]] = stored
                    unique[stored["scientific"]] = stored["id"]
                if len(unique) == 6:
                    break
            cell_photos[f"{x},{y}"] = list(unique.values())
        zone_index = {}
        for zone in zones:
            center = shape(zone["geometry"]).centroid
            cell = f"{math.floor(center.x / 0.05)},{math.floor(center.y / 0.05)}"
            nearby = [
                pid
                for pid in cell_photos[cell]
                if zone_distance_km(zone["geometry"], photos[pid]["lon"], photos[pid]["lat"]) <= 5
            ]
            nearest = next(iter(zone.get("nearby_places", [])), None)
            place = places_by_url.get((nearest or {}).get("url"))
            community_key = place.get("id") if place else None
            if place and community_key not in communities:
                lon, lat = place["center"]
                hits = collector.get_json(
                    COMMONS,
                    {
                        "action": "query",
                        "format": "json",
                        "list": "geosearch",
                        "gscoord": f"{lat}|{lon}",
                        "gsradius": 2000,
                        "gsnamespace": 6,
                        "gslimit": 20,
                    },
                )
                titles = [h["title"] for h in hits.get("query", {}).get("geosearch", [])]
                stored_ids = []
                for candidate in collector.commons(titles=titles, role="community") if titles else []:
                    if candidate.get("lon") is None or candidate.get("lat") is None:
                        continue
                    # Exact coordinates supplied by Commons; uncertainty remains explicitly unknown.
                    if (
                        zone_distance_km(
                            {"type": "Point", "coordinates": place["center"]},
                            candidate["lon"],
                            candidate["lat"],
                        )
                        > 2
                    ):
                        continue
                    stored = collector.store(candidate)
                    if stored:
                        photos[stored["id"]] = stored
                        stored_ids.append(stored["id"])
                    if len(stored_ids) == 3:
                        break
                communities[community_key] = {
                    "name": place["name"],
                    "center": place["center"],
                    "photo_ids": stored_ids,
                }
            zone_index[zone["alert_id"]] = {"nearby": nearby, "community_id": community_key}
        techniques = yaml.safe_load((CONFIG_DIR / "nbs/technique_photos.yaml").read_text(encoding="utf-8"))[
            "techniques"
        ]
        for technique in techniques:
            ids = []
            for candidate in technique.get("photos", []):
                # Only manually reviewed references may reach the published catalogue.
                if candidate.get("review") != "verified":
                    continue
                stored = collector.store({**candidate, "role": "technique"})
                if stored:
                    photos[stored["id"]] = stored
                    ids.append(stored["id"])
            technique["photo_ids"] = ids
            technique.pop("photos", None)
        soil_photos = []
        soils = {zone.get("soil", {}).get("wrb_name") for zone in zones if zone.get("soil")}
        for soil in sorted(soils - {None}):
            stored = next(
                (
                    p
                    for candidate in collector.commons(f"{soil} soil profile", role="soil")
                    if (p := collector.store(candidate))
                ),
                None,
            )
            if stored:
                photos[stored["id"]] = stored
            soil_photos.append({"name": soil, "photo_id": stored["id"] if stored else None})
        reference_file = CONFIG_DIR / "nbs/photo_references.yaml"
        references = (
            yaml.safe_load(reference_file.read_text(encoding="utf-8")).get("references", [])
            if reference_file.exists()
            else []
        )
        for candidate in references:
            if candidate.get("review") != "verified" or candidate.get("role") not in (
                "soil",
                "technique",
                "community",
            ):
                continue
            stored = collector.store(candidate)
            if not stored:
                continue
            photos[stored["id"]] = stored
            if candidate["role"] == "soil":
                for item in soil_photos:
                    if item["name"] in candidate.get("soil_names", []):
                        item["photo_id"] = stored["id"]
            elif candidate["role"] == "technique":
                for item in techniques:
                    if item["id"] in candidate.get("technique_ids", []):
                        item["photo_ids"].append(stored["id"])
            elif candidate.get("lat") is not None and candidate.get("lon") is not None:
                for community in communities.values():
                    if (
                        zone_distance_km(
                            {"type": "Point", "coordinates": community["center"]},
                            candidate["lon"],
                            candidate["lat"],
                        )
                        <= 2
                    ):
                        community["photo_ids"].append(stored["id"])
    result = {
        "version": 1,
        "aoi_id": aoi,
        "generated_at": datetime.now(UTC).isoformat(),
        "photos": photos,
        "species": species,
        "soils": soil_photos,
        "techniques": techniques,
        "communities": communities,
        "zones": zone_index,
        "warnings": list(dict.fromkeys(collector.errors)),
    }
    (output / f"{aoi}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "species_with_photo": sum(bool(s["photo_id"]) for s in species),
        "species_total": len(species),
        "nearby_observations": len({pid for ids in cell_photos.values() for pid in ids}),
        "community_photos": len({pid for c in communities.values() for pid in c["photo_ids"]}),
        "communities_with_photos": sum(bool(c["photo_ids"]) for c in communities.values()),
        "technique_photos": sum(len(t["photo_ids"]) for t in techniques),
        "soil_photos": sum(bool(s["photo_id"]) for s in soil_photos),
        "licensed_photos": len(photos),
        "warnings": result["warnings"],
    }
