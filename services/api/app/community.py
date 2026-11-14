"""Community summaries from published HV exposure and official event feeds."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from pyproj import Geod

GEOD = Geod(ellps="WGS84")


@lru_cache(maxsize=2)
def _read(path: Path, _mtime: int) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def publication(published: Path) -> dict | None:
    path = published / "community" / "ayacucho-huanta.json"
    try:
        return _read(path, path.stat().st_mtime_ns)
    except FileNotFoundError:
        return None


def observed_near(feed: dict, center: list[float], *, km: int, days: int, now: datetime) -> dict:
    events = []
    for feature in feed["features"]:
        props = feature["properties"]
        lon, lat = feature["geometry"]["coordinates"][:2]
        distance = GEOD.inv(*center, lon, lat)[2] / 1000
        when = datetime.fromisoformat(props["date"])
        if distance <= km and now - timedelta(days=days) <= when <= now:
            events.append({"date": props["date"], "km": round(distance, 2), **props["metrics"]})
    events.sort(key=lambda event: event["date"], reverse=True)
    return {
        "status": feed["status"],
        "updated_at": feed["last_updated"],
        "radius_km": km,
        "days": days,
        "events": events,
    }


def community_detail(
    entry: dict,
    feeds: dict,
    settings: dict,
    weather: dict | None = None,
    *,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(UTC)
    fire = observed_near(feeds["fires"], entry["center"], km=settings["fire_radius_km"], days=7, now=now)
    quakes = observed_near(feeds["quakes"], entry["center"], km=settings["quake_radius_km"], days=30, now=now)
    day_ago = now - timedelta(days=1)
    fires_today = [event for event in fire["events"] if datetime.fromisoformat(event["date"]) >= day_ago]
    quake_today = next(
        (
            e
            for e in quakes["events"]
            if e.get("magnitude", 0) >= settings["quake_magnitude"]
            and datetime.fromisoformat(e["date"]) >= day_ago
        ),
        None,
    )
    # Preserve evidence, including observations from the last successful refresh.
    reasons = []
    if fires_today:
        reasons.append(("red", "NASA FIRMS", "Foco térmico dentro del radio en 24 h", fires_today[0]["date"]))
    elif fire["events"]:
        reasons.append(
            ("orange", "NASA FIRMS", "Foco térmico dentro del radio en 7 días", fire["events"][0]["date"])
        )
    if quake_today:
        reasons.append(
            ("orange", "USGS", f"Sismo M ≥ {settings['quake_magnitude']:g} en 24 h", quake_today["date"])
        )
    conditions = (weather or {}).get("current")
    if conditions and not 0 <= (now.date() - date.fromisoformat(conditions["date"])).days <= 5:
        conditions = None
    if conditions:
        if conditions.get("heat_days", 0) >= settings["heat_days"]:
            reasons.append(
                ("orange", "NASA POWER", "Temperatura máxima sobre el percentil 90", conditions["date"])
            )
        if conditions.get("rain_ratio") is not None and conditions["rain_ratio"] < settings["rain_ratio"]:
            reasons.append(
                ("yellow", "NASA POWER", "Lluvia de 30 días por debajo del umbral", conditions["date"])
            )
        if (conditions.get("rain_ratio") is not None
                and conditions["rain_ratio"] >= settings["rain_excess_ratio"]):
            ratio = f"{conditions['rain_ratio']:.1f}".replace(".", ",")
            reasons.append((
                "orange", "NASA POWER",
                f"Lluvia de 30 días: {ratio} veces la climatología; "
                "vigilar condiciones asociadas a huaicos y deslizamientos",
                conditions["date"],
            ))
    rank = {"red": 0, "orange": 1, "yellow": 2}
    reasons.sort(key=lambda reason: rank[reason[0]])
    verified = not any(feed["stale"] or feed["status"] != "ok" for feed in feeds.values())
    weather_complete = conditions and conditions.get("rain_ratio") is not None
    level = reasons[0][0] if reasons else ("green" if verified and weather_complete else "unavailable")
    return {
        "as_of": now.isoformat(),
        "fire": fire,
        "quakes": quakes,
        "fires_today": len(fires_today),
        "indicator": {
            "level": level,
            "reasons": reasons,
            "live_complete": verified,
            "weather_at": conditions["date"] if conditions else None,
        },
        "rules": settings,
    }
