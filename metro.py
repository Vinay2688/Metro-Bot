import csv, os, time
from collections import Counter
from math import radians, sin, cos, asin, sqrt
from feed import fetch

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _load(name):
    with open(os.path.join(BASE_DIR, "gtfs", name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

_stops = _load("stops.txt")
STOPS = {s["stop_id"]: s["stop_name"] for s in _stops}
STOP_POINTS = [(float(s["stop_lat"]), float(s["stop_lon"]), s["stop_name"])
               for s in _stops if s["stop_lat"].strip() and s["stop_lon"].strip()]
_routes = _load("routes.txt")
ROUTES = {r["route_id"]: f'{r["route_short_name"]} {r["route_long_name"]}' for r in _routes}
ROUTE_SHORT = {r["route_id"]: r["route_short_name"] for r in _routes}
_trips = _load("trips.txt")
TRIP_HEADSIGN = {t["trip_id"]: t["trip_headsign"] for t in _trips}

# Jefferson Ave & University Ave. 'i' = inbound (toward downtown), 'o' = outbound.
STOP_DIRECTION = {
    "JEFUNIi": "toward_downtown",
    "JEFUNIo": "away_from_downtown",
}

def _route_ids(route):
    """Route IDs whose public number matches, e.g. '19'. Raises if none."""
    q = route.strip().lower()
    ids = {rid for rid, short in ROUTE_SHORT.items() if short.lower() == q}
    if not ids:
        raise ValueError(f"No Metro route numbered '{route}'.")
    return ids

def _distance_m(lat1, lon1, lat2, lon2):
    """Haversine distance in meters between two lat/lon points."""
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * 6371000 * asin(sqrt(a))

def next_departures(direction="both", limit=5, route=None):
    """Upcoming live departures from the UC campus stop, soonest first."""
    if direction == "both":
        wanted = set(STOP_DIRECTION)
    elif direction in STOP_DIRECTION.values():
        wanted = {s for s, d in STOP_DIRECTION.items() if d == direction}
    else:
        raise ValueError("direction must be 'toward_downtown', 'away_from_downtown' or 'both'")

    route_ids = _route_ids(route) if route else None
    now = time.time()
    results = []
    for ent in fetch("/tripupdate/tripupdates.pb").entity:
        t = ent.trip_update
        if route_ids is not None and t.trip.route_id not in route_ids:
            continue
        for stu in t.stop_time_update:
            if stu.stop_id in wanted and stu.departure.time > now:
                results.append({
                    "route": ROUTES.get(t.trip.route_id, t.trip.route_id),
                    "direction": STOP_DIRECTION[stu.stop_id],
                    "stop": STOPS.get(stu.stop_id, stu.stop_id),
                    "departs_at": time.strftime("%I:%M %p", time.localtime(stu.departure.time)),
                    "minutes_away": round((stu.departure.time - now) / 60),
                    "_ts": stu.departure.time,
                })
    results.sort(key=lambda r: r["_ts"])
    for r in results:
        del r["_ts"]
    return results[:limit]

def route_info(route):
    """Destinations of a route in each direction, from the schedule file."""
    ids = _route_ids(route)
    by_direction = {}
    for t in _trips:
        if t["route_id"] in ids:
            by_direction.setdefault(t["direction_id"], Counter())[t["trip_headsign"]] += 1
    return {
        "route": ROUTES[sorted(ids)[0]],
        "directions": [
            {"direction_id": d, "destinations": [h for h, _ in counts.most_common()]}
            for d, counts in sorted(by_direction.items())
        ],
    }

def bus_locations(route):
    """Where each active bus on a route is right now (from the live GPS feed)."""
    ids = _route_ids(route)
    now = time.time()
    buses = []
    for ent in fetch("/vehicle/vehiclepositions.pb").entity:
        v = ent.vehicle
        if v.trip.route_id not in ids:
            continue
        lat, lon = v.position.latitude, v.position.longitude
        dist, name = min((_distance_m(lat, lon, la, lo), n) for la, lo, n in STOP_POINTS)
        buses.append({
            "bus_id": v.vehicle.id,
            "heading_to": TRIP_HEADSIGN.get(v.trip.trip_id, "unknown"),
            "near_stop": name,
            "distance_from_stop_m": round(dist),
            "latitude": round(lat, 5),
            "longitude": round(lon, 5),
            "last_update_seconds_ago": round(now - v.timestamp) if v.timestamp else None,
        })
    return buses

if __name__ == "__main__":
    for d in next_departures("both", 2):
        print(d)
    print(route_info("19"))
    for b in bus_locations("19")[:3]:
        print(b)