"""Extract reviewed, intact field photos from licensed public reports."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import httpx
import pymupdf
import yaml

from .field_evidence import write_json
from .settings import CONFIG_DIR, INBOX, PUBLISHED

LICENSES = {
    "CC BY-NC-SA 4.0": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    "CC BY-NC-ND 4.0": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
    "CC BY-NC-ND 2.5 PE": "https://creativecommons.org/licenses/by-nc-nd/2.5/pe/",
}


def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.casefold()) if not unicodedata.combining(c))


def locate(entry, places):
    if "report_center" in entry:
        lon, lat = entry["report_center"]
        if -180 <= lon <= 180 and -90 <= lat <= 90:
            return lon, lat
    name = entry.get("match", entry["place"])
    matches = [
        p for p in places if p.get("kind") == "place" and normalized(p["name"]) == normalized(name)
        and (not entry.get("province") or p.get("province") == entry["province"])
    ]
    return matches[0]["center"] if len(matches) == 1 else None


def extract(document, entry):
    page = document[entry["page"] - 1]
    prefix = re.escape(entry.get("label", "Foto"))
    match = re.search(
        rf"(?m)^\s*({prefix} {entry['number']}[:.].*?)(?:(?<=\.)\s*\n|\n\s*\n|\Z)",
        page.get_text(), re.S,
    )
    if not match or entry["xref"] not in {row[0] for row in page.get_images()}:
        raise ValueError("La foto o leyenda del informe cambió")
    image = document.extract_image(entry["xref"])
    if image["ext"] not in ("jpeg", "png") or image["smask"]:
        raise ValueError("La foto requiere modificación para poder extraerse")
    return " ".join(match[1].split()), image


def publish(aoi):
    if not re.fullmatch(r"[a-z0-9-]+", aoi):
        raise ValueError("Territorio inválido")
    community = PUBLISHED / "community" / f"{aoi}.json"
    if not community.is_file():
        raise ValueError("Falta el catálogo de poblados")
    places = json.loads(community.read_text(encoding="utf-8"))["places"]
    config = yaml.safe_load((CONFIG_DIR / "field_sources.yaml").read_text(encoding="utf-8"))
    output = PUBLISHED / "field-photos"
    images = output / "images"
    images.mkdir(parents=True, exist_ok=True)
    INBOX.mkdir(parents=True, exist_ok=True)
    records = []
    for report in config["reports"]:
        if LICENSES.get(report["license"]) != report["license_url"]:
            continue
        pdf = INBOX / f"{report['id']}.pdf"
        if not pdf.exists():
            with httpx.stream("GET", report["url"], timeout=45) as response:
                response.raise_for_status()
                content = bytearray()
                for chunk in response.iter_bytes():
                    if len(content) + len(chunk) > 25_000_000:
                        raise ValueError("Informe demasiado grande")
                    content.extend(chunk)
        else:
            content = pdf.read_bytes()
        if hashlib.md5(content, usedforsecurity=False).hexdigest() != report["md5"]:
            raise ValueError("El PDF difiere del archivo verificado en el repositorio")
        if not pdf.exists():
            pdf.write_bytes(content)
        with pymupdf.open(stream=content, filetype="pdf") as document:
            for entry in report["photos"]:
                caption, image = extract(document, entry)
                location = locate(entry, places)
                filename = f"{report['id']}-{entry['number']}.{image['ext']}"
                Path(images / filename).write_bytes(image["image"])
                records.append({
                    "id": filename.rsplit(".", 1)[0], "title": entry["place"], "caption": caption,
                    "author": report["institution"], "taken_at": str(report["year"]),
                    "license": report["license"], "license_url": report["license_url"],
                    "source_url": f"{report['url']}#page={entry['page']}", "page": entry["page"],
                    "license_record_url": report["record_url"],
                    "image_url": f"/api/field-photos/images/{filename}",
                    "thumbnail_url": f"/api/field-photos/images/{filename}",
                    "lon": location[0] if location else None, "lat": location[1] if location else None,
                    "accuracy_m": None, "role": "field", "place": entry["place"],
                    "width": image["width"], "height": image["height"],
                    "modifications": "Imagen original del informe. El año corresponde al informe.",
                })
    write_json(output / f"{aoi}.json", records)
    return {"original_photos": len(records), "located": sum(p["lat"] is not None for p in records)}
