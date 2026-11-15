"""Field metadata must match the original photograph and a verified location."""
from io import BytesIO

import pymupdf
from PIL import Image

from sarlab_pipeline import field_photos


def test_field_photo_extracts_intact_pixels_and_original_caption():
    image = BytesIO()
    Image.new("RGB", (8, 8), "green").save(image, "JPEG")
    with pymupdf.open() as document:
        page = document.new_page()
        xref = page.insert_image(pymupdf.Rect(50, 50, 100, 100), stream=image.getvalue())
        page.insert_text((50, 125), "Foto 1: Deslizamiento cerca de un poblado.")
        page.insert_text((50, 148), "Un texto al margen.")
        caption, original = field_photos.extract(document, {"page": 1, "number": 1, "xref": xref})
    assert original["image"] == image.getvalue()
    assert caption == "Foto 1: Deslizamiento cerca de un poblado."


def test_field_location_rejects_loose_and_ambiguous_matches():
    place = {"kind": "place", "name": "Santa Lucía", "province": "Huamanga", "center": [-74.2, -13.2]}
    entry = {"place": "Santa Lucia", "province": "Huamanga"}
    assert field_photos.locate(entry, [place]) == place["center"]
    assert field_photos.locate({**entry, "place": "Santa"}, [place]) is None
    assert field_photos.locate(entry, [place, place]) is None
    assert field_photos.locate({**entry, "province": "Huanta"}, [place]) is None
