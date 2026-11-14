"""Publish an Ayacucho community index from the active HV analysis and public geography."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile

from shapely import make_valid
from shapely.geometry import Point, box, mapping, shape
from shapely.ops import unary_union

from sarlab_pipeline import exposure
from sarlab_pipeline import settings as S
from sarlab_pipeline.config import load_aois

AOI = "ayacucho-huanta"
PROVINCES = {
    "Huamanga": ("huamanga", 272029209),
    "Huanta": ("huanta", 346472191),
    "La Mar": ("la-mar", 2478936587),
}
COVER = ("cropland_ha", "grassland_ha", "forest_ha", "other_landcover_ha", "landcover_unmapped_ha")


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_districts(path: Path) -> dict:
    with ZipFile(path) as archive, archive.open("per_admin3.geojson") as source:
        raw = json.load(source)
    features = []
    for feature in raw["features"]:
        props = feature["properties"]
        if props["adm2_pcode"] not in {"PE0501", "PE0504", "PE0505"}:
            continue
        features.append({**feature, "properties": {
            "id": props["adm3_pcode"].removeprefix("PE"),
            "name": props["adm3_name"], "province": props["adm2_name"],
        }})
    return {"source": {"name": "IGN / OCHA · HDX COD-AB Perú", "url": "https://data.humdata.org/dataset/cod-ab-per",
                       "date": "2020-07-14", "license": "CC BY 3.0 IGO"}, "features": features}


def summarize(patches: list[dict]) -> dict:
    result = {}
    for key in (*COVER, "population"):
        values = [row[key] for row in patches if row.get(key) is not None]
        result[key] = round(sum(values), 3) if values else (None if patches else 0)
    return {
        **result,
        "zones": len(patches),
        "population_zones": sum(row.get("population") is not None for row in patches),
    }


def publish(districts: Path | None) -> dict:
    gcov = S.PROCESSED / AOI / "gcov"
    period = read(gcov / "active-comparison.json")["period"]
    active = gcov / period
    manifest = read(active / "manifest_hvhv.json")
    features = read(active / "alerts_hvhv.geojson")["features"]
    geo = read(S.ROOT / "apps/web/public/globe/peru-boundaries.geojson")
    coverage = box(*load_aois()[AOI].bbox)
    local = S.INTERIM / AOI
    published = read(S.PUBLISHED / "exposure" / f"{AOI}.json")
    patches = [
        (shape(feature["geometry"]), published["alerts"][feature["properties"]["id"]]) for feature in features
    ]
    places = read(local / "places.geojson")["features"]
    by_node = {feature["properties"]["osm_id"]: feature for feature in places}
    by_place = defaultdict(list)
    for _, metrics in patches:
        for place in metrics["nearby_places"] or []:
            by_place[place.get("url")].append(metrics)

    entries = []
    provinces = [
        (f["properties"]["name"], shape(f["geometry"]))
        for f in geo["features"]
        if f["properties"]["level"] == 2 and f["properties"]["name"] in PROVINCES
    ]
    boundaries = [
        (
            PROVINCES[name][0],
            name,
            "province",
            name,
            geometry,
            by_node[PROVINCES[name][1]]["geometry"]["coordinates"],
        )
        for name, geometry in provinces
    ]
    district_source = None
    if districts:
        dataset = read_districts(districts)
        district_source = dataset["source"]
        for feature in dataset["features"]:
            props = feature["properties"]
            geometry = make_valid(shape(feature["geometry"]))
            center = geometry.centroid
            if not geometry.covers(center):
                center = geometry.representative_point()
            boundaries.append(
                (
                    f"distrito-{props['id']}",
                    props["name"],
                    "district",
                    props["province"],
                    geometry,
                    [center.x, center.y],
                )
            )
    for key, name, kind, province, geometry, coordinates in boundaries:
        surveyed = geometry.intersection(coverage)
        rows = []
        for patch, metrics in patches:
            if surveyed.covers(patch):
                rows.append(metrics)
            elif surveyed.intersects(patch):
                clipped = surveyed.intersection(patch)
                if clipped.area:
                    rows.append(
                        {
                            **exposure._landcover(local / "worldcover.tif", mapping(clipped)),
                            "population": exposure._population(local / "worldpop.tif", mapping(clipped)),
                        }
                    )
        entries.append(
            {
                "id": key,
                "name": name,
                "kind": kind,
                "province": province,
                "center": coordinates,
                "impact": summarize(rows) if surveyed.area else None,
            }
        )
    for feature in places:
        props = feature["properties"]
        if not isinstance(props.get("name"), str) or not props["name"].strip():
            continue
        coordinates = feature["geometry"]["coordinates"]
        point = Point(coordinates)
        province = next((name for name, geometry in provinces if geometry.covers(point)), None)
        if province:
            entries.append(
                {
                    "id": feature["id"],
                    "name": props["name"],
                    "kind": "place",
                    "province": province,
                    "center": coordinates,
                    "url": props["url"],
                    "impact": summarize(by_place[props["url"]]) if coverage.covers(point) else None,
                }
            )
    province_union = unary_union([geometry for _, geometry in provinces])
    outside = []
    for patch, metrics in patches:
        remainder = patch.difference(province_union)
        if remainder.area:
            outside.append(metrics if remainder.equals(patch) else {
                **exposure._landcover(local / "worldcover.tif", mapping(remainder)),
                "population": exposure._population(local / "worldpop.tif", mapping(remainder)),
            })
    result = {
        "aoi": AOI,
        "period": manifest["dates"],
        "granules": manifest["provenance"]["granules"],
        "coverage_pct": manifest["quality"]["valid_area_pct"],
        "region": summarize([m for _, m in patches]),
        "outside_provinces": summarize(outside),
        "sources": published["sources"],
        "district_source": district_source,
        "places": entries,
    }
    folder = S.PUBLISHED / "community"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{AOI}.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    temporary.replace(path)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--districts", type=Path, help="Official HDX district GeoJSON archive")
    datum = publish(parser.parse_args().districts)
    print(json.dumps({"places": len(datum["places"]), "region": datum["region"]}))
