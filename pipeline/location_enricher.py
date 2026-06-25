"""
location_enricher.py
--------------------
Fills festival coordinates (Nominatim) and seeds the `stages` table so v2.8's
phone-background generator has a point per stage.

Two layers:
  1. festivals.latitude/longitude — geocoded from "venue, city, state" via
     Nominatim and cached (geocoded_at). Re-runs skip already-geocoded rows, so
     the daily cron never re-hits the API.
  2. stages(festival_id, name) — one row per distinct lineups.stage. Lollapalooza
     uses a known published Grant Park layout; other festivals fall back to the
     festival's venue coordinate, spread slightly so pins don't overlap.

Idempotent: festival geocode is cached; stages upsert on (festival_id, name).

Run:
    python location_enricher.py                      # all festivals
    python location_enricher.py --festival lollapalooza
    python location_enricher.py --force              # re-geocode even if cached
    python location_enricher.py --self-test          # offline checks, no DB

Schedule: daily via etl_daily.yml (cheap — cached after first run).
"""

from __future__ import annotations

import os
import argparse
from datetime import datetime, timezone

from geocoder import geocode

# Heavy deps (supabase, rich, dotenv) imported lazily in the DB path so
# --self-test runs with only requests/tenacity present.

# Approximate published Grant Park stage layout (north→south), 2026 footprint.
# Lat/lng are approximate — good enough for a wallpaper map pin; refine with
# surveyed coordinates if precision ever matters. ponytail: approximate layout,
# upgrade to surveyed coords if v2.8 needs sub-block accuracy.
LOLLA_STAGES: dict[str, tuple[float, float]] = {
    "Bud Light Stage":    (41.8815, -87.6205),
    "T-Mobile Stage":     (41.8800, -87.6185),
    "Tito's Stage":       (41.8770, -87.6230),
    "Allianz Stage":      (41.8760, -87.6180),
    "Perry's Stage":      (41.8735, -87.6235),
    "BMI Stage":          (41.8720, -87.6190),
    "Airbnb Stage":       (41.8700, -87.6225),
    "Kidzapalooza Stage": (41.8690, -87.6200),
}

KNOWN_STAGES: dict[str, dict[str, tuple[float, float]]] = {
    "lollapalooza": LOLLA_STAGES,
}


def spread(lat: float, lng: float, i: int, n: int) -> tuple[float, float]:
    """Deterministic small offset so n stages sharing a venue centroid don't
    stack on one pixel. ~50–150 m ring; stable across re-runs for idempotency."""
    import math
    if n <= 1:
        return lat, lng
    angle = 2 * math.pi * i / n
    r = 0.0010  # ~110 m in latitude degrees
    return round(lat + r * math.cos(angle), 6), round(lng + r * math.sin(angle), 6)


# ── DB path ────────────────────────────────────────────────────

def get_supabase():
    from dotenv import load_dotenv
    from supabase import create_client
    load_dotenv()
    return create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def geocode_festival(sb, festival: dict, force: bool, console) -> tuple[float, float] | None:
    """Return (lat, lng) for a festival, geocoding + caching if needed."""
    if festival.get("latitude") is not None and festival.get("geocoded_at") and not force:
        return festival["latitude"], festival["longitude"]

    parts = [festival.get(k) for k in ("venue", "city", "state", "country")]
    query = ", ".join(p for p in parts if p)
    coords = geocode(query)
    if not coords:  # fall back to city-level
        city_query = ", ".join(p for p in (festival.get("city"), festival.get("state"), festival.get("country")) if p)
        if city_query and city_query != query:
            coords = geocode(city_query)
    if not coords:
        console.log(f"  [red]no geocode for {festival['slug']} ({query!r})")
        return None

    sb.table("festivals").update({
        "latitude": coords[0],
        "longitude": coords[1],
        "geocoded_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", festival["id"]).execute()
    console.log(f"  [green]geocoded {festival['slug']} -> {coords[0]:.4f}, {coords[1]:.4f}")
    return coords


def seed_stages(sb, festival: dict, base: tuple[float, float] | None, console) -> int:
    """Upsert one stages row per distinct lineups.stage for this festival."""
    rows = (
        sb.table("lineups").select("stage")
        .eq("festival_id", festival["id"]).not_.is_("stage", "null").execute()
    )
    names = sorted({r["stage"] for r in rows.data if r.get("stage")})
    if not names:
        return 0

    known = KNOWN_STAGES.get(festival["slug"], {})
    written = 0
    for i, name in enumerate(names):
        if name in known:
            lat, lng, src = known[name][0], known[name][1], "known"
        elif base:
            lat, lng = spread(base[0], base[1], i, len(names))
            src = "venue_centroid"
        else:
            continue  # no coordinates available at all — skip rather than write nulls
        sb.table("stages").upsert(
            {"festival_id": festival["id"], "name": name,
             "latitude": lat, "longitude": lng, "coords_source": src},
            on_conflict="festival_id,name",
        ).execute()
        written += 1
    return written


def main() -> None:
    from rich.console import Console
    console = Console()

    parser = argparse.ArgumentParser(description="Geocode festivals + seed stage coordinates")
    parser.add_argument("--festival", type=str, help="Festival slug to target")
    parser.add_argument("--force", action="store_true", help="Re-geocode even if cached")
    args = parser.parse_args()

    sb = get_supabase()
    cols = "id, slug, venue, city, state, country, latitude, longitude, geocoded_at"
    q = sb.table("festivals").select(cols)
    if args.festival:
        q = q.eq("slug", args.festival)
    festivals = q.execute().data or []

    console.rule(f"[bold]Location enricher — {len(festivals)} festival(s)")
    total_stages = 0
    for f in festivals:
        console.log(f"[cyan]{f['slug']}")
        base = geocode_festival(sb, f, args.force, console)
        total_stages += seed_stages(sb, f, base, console)
    console.print(f"[bold green]Done.[/bold green] {total_stages} stage rows upserted.")


def _demo() -> None:
    # Single stage: no offset.
    assert spread(41.0, -87.0, 0, 1) == (41.0, -87.0)
    # Multiple stages: distinct, deterministic, and near the base.
    a = spread(41.0, -87.0, 0, 4)
    b = spread(41.0, -87.0, 1, 4)
    assert a != b
    assert spread(41.0, -87.0, 1, 4) == b  # stable across calls (idempotent)
    assert abs(a[0] - 41.0) < 0.002 and abs(a[1] + 87.0) < 0.002
    # Every known Lolla stage has a coordinate.
    assert len(LOLLA_STAGES) == 8 and all(v for v in LOLLA_STAGES.values())
    print("location_enricher: all checks passed")


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        _demo()
    else:
        main()
