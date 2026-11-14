"""Procesa el par GCOV de Ayacucho y activa la comparación tras verificarla."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from sarlab_pipeline import settings
from sarlab_pipeline.analysis import timeseries
from sarlab_pipeline.ingest import ingest_inbox, load_catalog
from sarlab_pipeline.readers.hdf5_inspect import inspect
from sarlab_pipeline.workflows import change_multi

AOI = "ayacucho-huanta"
DATES = ("2026-06-24", "2026-10-10")
PERIOD = "__".join(DATES)
MIN_COVERAGE_PCT = 80


def _files() -> list[Path]:
    entries = load_catalog()["items"]
    files = []
    for day in DATES:
        matches = [settings.RAW / item["path"] for name, item in entries.items()
                   if "_GCOV_" in name and "_147_A_171_2005_DHDH_A_" in name
                   and f"_{day.replace('-', '')}T" in name and "_P05023_" in name]
        if len(matches) != 1 or not matches[0].is_file():
            raise SystemExit(f"Falta el GCOV seleccionado del {day}. Ejecuta tools/download_approved.py.")
        files.append(matches[0])
    return files


def main() -> None:
    print(json.dumps(ingest_inbox(), ensure_ascii=False, indent=2), flush=True)
    paths = _files()
    inspected = [line for path in paths for line in (path.name, *inspect(path))]
    (settings.CATALOG / "ayacucho-huanta-inspect.txt").write_text("\n".join(inspected), encoding="utf-8")
    processed = settings.PROCESSED
    final_dir = processed / AOI / "gcov" / PERIOD
    active_file = final_dir.parent / "active-comparison.json"
    if active_file.is_file() and json.loads(active_file.read_text(encoding="utf-8")).get("period") == PERIOD:
        print(f"La comparación {PERIOD} ya está activa.")
        return
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".ayacucho-g1-", dir=processed) as temporary:
        staging = Path(temporary)
        settings.PROCESSED = staging
        try:
            change = change_multi(AOI, *paths)
            series = timeseries(AOI, paths)
        finally:
            settings.PROCESSED = processed
        directory = staging / AOI / "gcov" / PERIOD
        coverage = {}
        for pol in ("HHHH", "HVHV"):
            manifest_path = directory / f"manifest_{pol.lower()}.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            coverage[pol] = manifest["quality"]["valid_area_pct"]
            manifest["cog_path"] = str(final_dir / Path(manifest["cog_path"]).name)
            for key in ("before_cog_path", "after_cog_path"):
                manifest["comparison"][key] = str(final_dir / Path(manifest["comparison"][key]).name)
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        result = {"common_valid_pct": coverage, "summary": change["summary"], "samples": series["samples"]}
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        per_date = [sample[pol]["valid_pct"] if sample[pol] else 0
                    for sample in series["samples"] for pol in coverage]
        if min(*coverage.values(), *per_date) < MIN_COVERAGE_PCT:
            raise SystemExit(
                f"G1 requiere {MIN_COVERAGE_PCT} % de cobertura válida. La comparación previa sigue activa.")
        (directory.parent / "timeseries.json").replace(directory / "timeseries.json")
        directory.rename(final_dir)
        select = staging / "active-comparison.json"
        select.write_text(json.dumps({"period": PERIOD}), encoding="utf-8")
        select.replace(active_file)
    print(f"Comparación activa: {PERIOD}", flush=True)


if __name__ == "__main__":
    main()
