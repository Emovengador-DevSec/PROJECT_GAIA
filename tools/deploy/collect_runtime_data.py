"""Stage the published inputs read by the live API for a portable Docker build."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from shutil import copyfile

ROOT = Path(__file__).resolve().parents[2]
STAGING = ROOT / "deploy"
DATA = ROOT / "data"


def collect(destination: Path) -> tuple[int, int]:
    processed = DATA / "03_processed"
    files: dict[Path, Path] = {}
    documents: dict[Path, dict] = {}
    active_alerts: dict[str, set[str]] = {}

    def add(path: Path) -> None:
        if not path.resolve().is_relative_to(DATA.resolve()) or not path.is_file():
            raise ValueError(f"Archivo publicado ausente o fuera de data/: {path.name}")
        files[path.relative_to(DATA)] = path

    for manifest_path in sorted(processed.glob("*/*/*/manifest*.json")):
        period_dir = manifest_path.parent
        product_dir = period_dir.parent
        selection = product_dir / "active-comparison.json"
        if product_dir.name == "gcov" and selection.is_file():
            if json.loads(selection.read_text(encoding="utf-8"))["period"] != period_dir.name:
                continue
            add(selection)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for section in (manifest, manifest.get("comparison") or {}):
            for key, value in section.items():
                if key.endswith("cog_path"):
                    cog = period_dir / Path(value.replace("\\", "/")).name
                    if cog.suffix.lower() not in {".tif", ".tiff"}:
                        raise ValueError(f"Formato COG inesperado en {manifest_path.name}")
                    add(cog)
                    section[key] = cog.relative_to(processed).as_posix()
        documents[manifest_path.relative_to(DATA)] = manifest
        zone_alerts = active_alerts.setdefault(manifest["aoi_id"], set())
        for alert_path in sorted(period_dir.glob("alerts*.geojson")):
            add(alert_path)
            features = json.loads(alert_path.read_text(encoding="utf-8"))["features"]
            zone_alerts.update(feature["properties"]["id"] for feature in features)
        for name in ("polarizations.json", "timeseries.json"):
            path = period_dir / name
            if path.is_file():
                add(path)
        validation = DATA / "04_published" / "validation" / f"{manifest['id']}.json"
        if validation.is_file():
            add(validation)

    if not documents:
        raise ValueError("No hay manifiestos NISAR publicados para el contenedor.")
    for zone, ids in active_alerts.items():
        path = DATA / "04_published" / "exposure" / f"{zone}.json"
        if path.is_file():
            report = json.loads(path.read_text(encoding="utf-8"))
            report["alerts"] = {key: value for key, value in report["alerts"].items() if key in ids}
            if "alert_count" in report:
                report["alert_count"] = len(report["alerts"])
            documents[path.relative_to(DATA)] = report
    # Every published layer the API reads (zone sheets, soil, photos, imagery, climate...).
    # Exposure reports are filtered above; validation files follow the active manifests.
    for path in sorted((DATA / "04_published").rglob("*")):
        relative = path.relative_to(DATA / "04_published")
        if path.is_file() and relative.parts[0] not in {"exposure", "validation"}:
            add(path)
    for pattern in ("catalog/nisar_*.json", "catalog/live/*.json"):
        for path in sorted(DATA.glob(pattern)):
            add(path)

    destination.mkdir(parents=True)
    for relative, source in files.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        copyfile(source, target)
    for relative, document in documents.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(document, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    size = sum(path.stat().st_size for path in destination.rglob("*") if path.is_file())
    return len(files) + len(documents), size


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=STAGING / "data")
    destination = parser.parse_args().output.resolve()
    if not destination.is_relative_to(STAGING.resolve()) or destination == STAGING.resolve():
        parser.error("El destino debe ser una carpeta nueva dentro de deploy/.")
    if destination.exists():
        parser.error("El destino ya existe. Usa otra carpeta o retira la copia de despliegue anterior.")
    count, size = collect(destination)
    print(f"{count} archivos de ejecución · {size / 1_000_000:.2f} MB · {destination}")


if __name__ == "__main__":
    main()
