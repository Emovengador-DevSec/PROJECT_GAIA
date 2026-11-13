"""Las celdas conservan cantidad, fechas y posición de las detecciones de prueba."""

from shapely.geometry import Point, shape

from app.fire_cells import aggregate


def test_grouped_fires_preserve_counts_and_members():
    features = [
        {"geometry": {"type": "Point", "coordinates": [-74.1 + i * .001, -13.1]},
         "properties": {"id": f"test-{i}", "kind": "fire", "date": f"2026-11-13T0{i}:00:00+00:00"}}
        for i in range(3)
    ]
    features.append({"geometry": {"type": "Point", "coordinates": [-75, -14]},
                     "properties": {"id": "quake", "kind": "quake"}})
    cells = aggregate(features)
    assert sum(cell["properties"]["metrics"]["count"] for cell in cells) == 3
    assert len(cells) == 1
    cell = cells[0]
    assert len(cell["properties"]["members"]) == 3
    assert cell["properties"]["first_date"] < cell["properties"]["date"]
    assert all(shape(cell["geometry"]).covers(Point(*f["geometry"]["coordinates"])) for f in features[:3])
    assert cell["properties"]["source_kind"] == "complementary"
