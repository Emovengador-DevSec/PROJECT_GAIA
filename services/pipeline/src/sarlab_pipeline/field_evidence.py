"""Local field-evidence publication helpers."""
import json
from tempfile import NamedTemporaryFile


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False, mode="w", encoding="utf-8") as file:
        temporary = path.parent / file.name
        json.dump(data, file, ensure_ascii=False, indent=2)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
