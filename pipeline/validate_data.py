"""
validate_data.py
----------------
Sanity checks that fail on missing or contradictory dates / locations.

Two modes:
  --self-test : offline. Runs the validators against the REAL curated Lolla 2026
                schedule (must be clean) plus good/bad fixtures (must pass/fail as
                expected). No DB, no secrets — this is the CI gate.
  (default)   : live. Validates every festival in Supabase and exits non-zero if
                any check fails. Needs the service-role key; run manually or in
                etl_daily.

Validations:
  festival : has start/end (or flagged dates_estimated); start <= end; has
             venue or city; has lat/lng in range.
  schedule : each set has day/stage/start/end; day within the festival range;
             end after start; no two sets overlap on the same stage+day.
  stages   : every stage row has coordinates.

Run:
    python validate_data.py --self-test
    python validate_data.py --festival lollapalooza
"""

from __future__ import annotations

import os
import sys
import argparse
from collections import defaultdict


def _mins(t: str) -> int:
    # Accept "HH:MM" (curated schedule) and "HH:MM:SS" (Postgres time columns).
    h, m = t.split(":")[:2]
    return int(h) * 60 + int(m)


# ── Pure validators (no DB) ────────────────────────────────────

def validate_festival(f: dict) -> list[str]:
    slug = f.get("slug", "?")
    errors: list[str] = []
    start, end = f.get("start_date"), f.get("end_date")
    if not start or not end:
        if not f.get("dates_estimated"):
            errors.append(f"{slug}: missing start/end date and not flagged dates_estimated")
    elif start > end:
        errors.append(f"{slug}: start_date {start} is after end_date {end}")

    if not f.get("venue") and not f.get("city"):
        errors.append(f"{slug}: missing both venue and city")

    lat, lng = f.get("latitude"), f.get("longitude")
    if lat is None or lng is None:
        errors.append(f"{slug}: missing coordinates (not geocoded)")
    elif not (-90 <= lat <= 90 and -180 <= lng <= 180):
        errors.append(f"{slug}: coordinates out of range ({lat}, {lng})")
    return errors


def validate_schedule(entries: list[dict], start_date: str | None, end_date: str | None) -> list[str]:
    """entries: dicts with artist, stage, day, start, end (start/end as HH:MM)."""
    errors: list[str] = []
    for e in entries:
        who = e.get("artist", "?")
        for field in ("day", "stage", "start", "end"):
            if not e.get(field):
                errors.append(f"{who}: missing {field}")
        day = e.get("day")
        if day and start_date and end_date and not (start_date <= day <= end_date):
            errors.append(f"{who}: day {day} outside festival range {start_date}..{end_date}")
        if e.get("start") and e.get("end") and _mins(e["end"]) <= _mins(e["start"]):
            errors.append(f"{who}: end {e['end']} not after start {e['start']}")

    # No two sets overlap on one stage on one day.
    by_stage: dict[tuple, list[dict]] = defaultdict(list)
    for e in entries:
        if all(e.get(k) for k in ("stage", "day", "start", "end")):
            by_stage[(e["stage"], e["day"])].append(e)
    for (stage, day), group in by_stage.items():
        ordered = sorted(group, key=lambda x: _mins(x["start"]))
        for a, b in zip(ordered, ordered[1:]):
            if _mins(b["start"]) < _mins(a["end"]):
                errors.append(
                    f"overlap on {stage} {day}: {a.get('artist')} "
                    f"({a['start']}-{a['end']}) vs {b.get('artist')} ({b['start']})"
                )
    return errors


def validate_stages(stages: list[dict]) -> list[str]:
    return [
        f"stage '{s.get('name')}' (festival {s.get('festival_id', '?')[:8]}) missing coordinates"
        for s in stages
        if s.get("latitude") is None or s.get("longitude") is None
    ]


# ── Live DB mode ───────────────────────────────────────────────

def _run_live(target_slug: str | None) -> int:
    from dotenv import load_dotenv
    from supabase import create_client
    from rich.console import Console
    load_dotenv()
    console = Console()
    sb = create_client(os.environ["NEXT_PUBLIC_SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

    fcols = "id, slug, venue, city, start_date, end_date, dates_estimated, latitude, longitude"
    fq = sb.table("festivals").select(fcols)
    if target_slug:
        fq = fq.eq("slug", target_slug)
    festivals = fq.execute().data or []

    all_errors: list[str] = []
    for f in festivals:
        errs = validate_festival(f)
        lineups = sb.table("lineups").select(
            "stage, day, set_time_start, set_time_end, artists(name)"
        ).eq("festival_id", f["id"]).execute().data or []
        entries = [{
            "artist": (r.get("artists") or {}).get("name"),
            "stage": r.get("stage"), "day": r.get("day"),
            "start": r.get("set_time_start"), "end": r.get("set_time_end"),
        } for r in lineups]
        # Only enforce per-set completeness/overlap where the festival actually
        # carries set times (scraped name-only lineups legitimately lack them).
        timed = [e for e in entries if e["start"] and e["end"]]
        errs += validate_schedule(timed, f.get("start_date"), f.get("end_date"))
        stages = sb.table("stages").select("name, festival_id, latitude, longitude").eq(
            "festival_id", f["id"]).execute().data or []
        errs += validate_stages(stages)

        if errs:
            console.print(f"[red]✗ {f['slug']}[/red]")
            for e in errs:
                console.print(f"    {e}")
            all_errors += errs
        else:
            console.print(f"[green]✓ {f['slug']}[/green]")

    if all_errors:
        console.print(f"\n[bold red]{len(all_errors)} validation error(s).[/bold red]")
        return 1
    console.print(f"\n[bold green]All {len(festivals)} festival(s) valid.[/bold green]")
    return 0


# ── Offline self-test (CI gate) ────────────────────────────────

def _self_test() -> None:
    from lolla_2026_schedule import SCHEDULE

    # 1. The REAL curated Lolla schedule must be internally consistent.
    entries = [{"artist": e["name"], "stage": e["stage"], "day": e["day"],
                "start": e["start"], "end": e["end"]} for e in SCHEDULE]
    errs = validate_schedule(entries, "2026-07-30", "2026-08-02")
    assert errs == [], f"curated Lolla schedule is not clean:\n  " + "\n  ".join(errs)

    # 2. A good festival passes.
    assert validate_festival({
        "slug": "x", "start_date": "2026-08-01", "end_date": "2026-08-02",
        "venue": "Grant Park", "latitude": 41.87, "longitude": -87.62,
    }) == []

    # 3. Broken festivals are caught.
    assert validate_festival({"slug": "x", "venue": "V"})  # no dates, no coords
    assert validate_festival({
        "slug": "x", "start_date": "2026-08-03", "end_date": "2026-08-01",
        "city": "C", "latitude": 1, "longitude": 2,
    })  # start after end

    # 4. Overlap + out-of-range day + bad time order are caught.
    bad = validate_schedule([
        {"artist": "A", "stage": "S", "day": "2026-08-01", "start": "12:00", "end": "13:00"},
        {"artist": "B", "stage": "S", "day": "2026-08-01", "start": "12:30", "end": "13:30"},  # overlaps A
        {"artist": "C", "stage": "S", "day": "2026-09-09", "start": "10:00", "end": "11:00"},  # out of range
        {"artist": "D", "stage": "S", "day": "2026-08-01", "start": "15:00", "end": "14:00"},  # end<=start
    ], "2026-08-01", "2026-08-02")
    assert any("overlap" in e for e in bad), bad
    assert any("outside festival range" in e for e in bad), bad
    assert any("not after start" in e for e in bad), bad

    # 5. Missing stage coordinates are caught.
    assert validate_stages([{"name": "S", "festival_id": "abcd1234", "latitude": None, "longitude": None}])

    # 6. Postgres time columns serialize as HH:MM:SS — must parse, not crash.
    assert _mins("20:30:00") == 1230
    assert validate_schedule([
        {"artist": "A", "stage": "S", "day": "2026-08-01", "start": "12:00:00", "end": "13:00:00"},
        {"artist": "B", "stage": "S", "day": "2026-08-01", "start": "12:30:00", "end": "13:30:00"},
    ], "2026-08-01", "2026-08-02") and True  # overlap still detected on HH:MM:SS

    print("validate_data: all checks passed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate festival dates/locations/schedules")
    parser.add_argument("--self-test", action="store_true", help="offline checks (CI gate)")
    parser.add_argument("--festival", type=str, help="limit live mode to one slug")
    args = parser.parse_args()

    if args.self_test:
        _self_test()
        return
    sys.exit(_run_live(args.festival))


if __name__ == "__main__":
    main()
