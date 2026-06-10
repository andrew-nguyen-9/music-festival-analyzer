"""
lineup_scraper.py
-----------------
Fetches festival lineups from:
  1. Ticketmaster Discovery API (primary — upcoming festivals, day-by-day)
  2. Setlist.fm API (fallback — past/historical festivals, by venue)

For each festival it upserts artists and lineup rows into Supabase.
Headliners are inferred from billing position (first 3 per day).

Run:
    python lineup_scraper.py                        # all festivals, current year
    python lineup_scraper.py --festival lollapalooza
    python lineup_scraper.py --dry-run              # no DB writes, just print
    python lineup_scraper.py --source ticketmaster  # force one source
    python lineup_scraper.py --source setlistfm
"""

import os
import re
import time
import logging
import argparse
from datetime import date, datetime
from slugify import slugify
from dotenv import load_dotenv

import requests
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.console import Console
from rich.progress import track

load_dotenv()
console = Console()
log = logging.getLogger(__name__)

# ── Per-festival configuration ─────────────────────────────────
# ticketmaster_keyword: search term for TM Discovery API
# setlistfm_venue:      venue name used in Setlist.fm search
# headliners_per_day:   how many top-billed artists to mark as headliners
FESTIVAL_CONFIG = {
    "lollapalooza": {
        "ticketmaster_keyword": "Lollapalooza",
        "setlistfm_venue": "Grant Park",
        "headliners_per_day": 3,
    },
    "coachella": {
        "ticketmaster_keyword": "Coachella Valley Music",
        "setlistfm_venue": "Empire Polo Club",
        "setlistfm_tour": "Coachella Valley Music and Arts Festival",
        "headliners_per_day": 3,
    },
    "electric-daisy-carnival": {
        "ticketmaster_keyword": "Electric Daisy Carnival Las Vegas",
        "setlistfm_venue": "Las Vegas Motor Speedway",
        "headliners_per_day": 3,
    },
    "south-by-southwest": {
        "ticketmaster_keyword": "SXSW",
        "setlistfm_venue": "Austin",
        "headliners_per_day": 2,
    },
    "outside-lands": {
        "ticketmaster_keyword": "Outside Lands",
        "setlistfm_venue": "Golden Gate Park",
        "headliners_per_day": 3,
    },
    "ultra-music-festival": {
        "ticketmaster_keyword": "Ultra Music Festival",
        "setlistfm_venue": "Bayfront Park",
        "headliners_per_day": 3,
    },
    "bonnaroo-music-and-arts-festival": {
        "ticketmaster_keyword": "Bonnaroo",
        "setlistfm_venue": "Bonnaroo Music and Arts Festival",
        "headliners_per_day": 3,
    },
    "austin-city-limits-music-festival": {
        "ticketmaster_keyword": "Austin City Limits Music Festival",
        "setlistfm_venue": "Zilker Park",
        "headliners_per_day": 3,
    },
    "governors-ball": {
        "ticketmaster_keyword": "Governors Ball",
        "setlistfm_venue": "Governors Ball Music Festival",
        "headliners_per_day": 3,
    },
    "stagecoach": {
        "ticketmaster_keyword": "Stagecoach Festival",
        "setlistfm_venue": "Empire Polo Club",
        "headliners_per_day": 2,
    },
    "bottlerock-napa-valley": {
        "ticketmaster_keyword": "BottleRock Napa",
        "setlistfm_venue": "Napa Valley Expo",
        "headliners_per_day": 2,
    },
    "rolling-loud": {
        "ticketmaster_keyword": "Rolling Loud",
        "setlistfm_venue": "Hard Rock Stadium",
        "headliners_per_day": 3,
    },
    "firefly-music-festival": {
        "ticketmaster_keyword": "Firefly Music Festival",
        "setlistfm_venue": "The Woodlands",
        "headliners_per_day": 2,
    },
    "hangout-music-festival": {
        "ticketmaster_keyword": "Hangout Music Festival",
        "setlistfm_venue": "Gulf Shores Public Beach",
        "headliners_per_day": 2,
    },
    "new-orleans-jazz-heritage-festival": {
        "ticketmaster_keyword": "New Orleans Jazz Heritage Festival",
        "setlistfm_venue": "Fair Grounds Race Course",
        "headliners_per_day": 2,
    },
    "newport-folk-festival": {
        "ticketmaster_keyword": "Newport Folk Festival",
        "setlistfm_venue": "Fort Adams State Park",
        "headliners_per_day": 2,
    },
    "essence-festival-of-culture": {
        "ticketmaster_keyword": "Essence Festival",
        "setlistfm_venue": "Caesars Superdome",
        "headliners_per_day": 2,
    },
    "life-is-beautiful": {
        "ticketmaster_keyword": "Life is Beautiful Festival",
        "setlistfm_venue": "Downtown Las Vegas",
        "headliners_per_day": 2,
    },
    "pitchfork-music-festival": {
        "ticketmaster_keyword": "Pitchfork Music Festival",
        "setlistfm_venue": "Union Park",
        "headliners_per_day": 2,
    },
    "hard-summer": {
        "ticketmaster_keyword": "Hard Summer",
        "setlistfm_venue": "Auto Club Speedway",
        "headliners_per_day": 2,
    },
    "ohana-festival": {
        "ticketmaster_keyword": "Ohana Festival",
        "setlistfm_venue": "Doheny State Beach",
        "headliners_per_day": 2,
    },
    "summer-smash": {
        "ticketmaster_keyword": "Summer Smash",
        "setlistfm_venue": "Douglass Park",
        "headliners_per_day": 2,
    },
    "when-we-were-young": {
        "ticketmaster_keyword": "When We Were Young Festival",
        "setlistfm_venue": "Las Vegas Festival Grounds",
        "headliners_per_day": 2,
    },
    "day-n-vegas": {
        "ticketmaster_keyword": "Day N Vegas",
        "setlistfm_venue": "Las Vegas Festival Grounds",
        "headliners_per_day": 2,
    },
    "voodoo-fest": {
        "ticketmaster_keyword": "Voodoo Fest",
        "setlistfm_venue": "City Park",
        "headliners_per_day": 2,
    },
    "electric-forest": {
        "ticketmaster_keyword": "Electric Forest",
        "setlistfm_venue": "Double JJ Resort",
        "headliners_per_day": 2,
    },
}


# ── API clients ────────────────────────────────────────────────

def get_supabase() -> Client:
    return create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def tm_get(path: str, params: dict) -> dict:
    params["apikey"] = os.environ["TICKETMASTER_API_KEY"]
    resp = requests.get(
        f"https://app.ticketmaster.com/discovery/v2/{path}",
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def setlistfm_get(path: str, params: dict) -> dict:
    resp = requests.get(
        f"https://api.setlist.fm/rest/1.0/{path}",
        params=params,
        headers={
            "x-api-key": os.environ["SETLIST_API_KEY"],
            "Accept": "application/json",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ── Ticketmaster source ────────────────────────────────────────

def _is_main_festival_event(event_name: str, keyword: str) -> bool:
    """True if this TM event is the main festival, not an aftershow/side event."""
    name_lower = event_name.lower().strip()
    keyword_lower = keyword.lower().strip()
    # Accept if the event name IS the keyword (or very close)
    if name_lower == keyword_lower:
        return True
    # Accept if name starts with the keyword and has no extra text indicating a side event
    side_event_markers = ["aftershow", "after show", "after-show", "official", "feat", "present", "sold out"]
    if any(m in name_lower for m in side_event_markers):
        return False
    # Accept short names that are basically the festival (e.g. "Lollapalooza 2026")
    if name_lower.startswith(keyword_lower):
        return True
    return False


def fetch_tm_lineup(keyword: str, year: int, festival_slug: str = "") -> list[dict]:
    """
    Returns a list of day-dicts:
      { "date": "2026-07-31", "artists": [{"name": ..., "image_url": ...}], "headliner_count": N }
    One entry per festival day found in TM.
    """
    data = tm_get("events.json", {
        "keyword": keyword,
        "classificationName": "Music",
        "countryCode": "US",
        "size": 50,
        "sort": "date,asc",
    })

    events = data.get("_embedded", {}).get("events", [])
    days: list[dict] = []

    for event in events:
        event_name = event.get("name", "")
        event_date = event.get("dates", {}).get("start", {}).get("localDate", "")

        if not event_date or not event_date.startswith(str(year)):
            continue

        # Skip aftershows and single-artist side events
        if not _is_main_festival_event(event_name, keyword):
            continue

        attractions = event.get("_embedded", {}).get("attractions", [])

        # Skip the first attraction if it's the festival itself
        keyword_stem = keyword.split()[0].lower()
        if attractions and keyword_stem in attractions[0].get("name", "").lower():
            attractions = attractions[1:]

        # Require at least 5 artists to confirm this is a real festival day entry
        if len(attractions) < 5:
            continue

        artists = []
        for att in attractions:
            name = att.get("name", "").strip()
            if not name:
                continue
            image_url = None
            for img in att.get("images", []):
                if not img.get("fallback") and img.get("width", 0) >= 300:
                    image_url = img["url"]
                    break
            artists.append({"name": name, "image_url": image_url})

        if artists:
            days.append({
                "date": event_date,
                "artists": artists,
                "headliner_count": FESTIVAL_CONFIG.get(festival_slug, {}).get("headliners_per_day", 2),
            })

    return days


# ── Setlist.fm source ──────────────────────────────────────────

def fetch_setlistfm_lineup(venue_name: str, year: int, tour_name: str = "") -> list[dict]:
    """
    Returns a list of artist-dicts from Setlist.fm (no per-day breakdown).
    Used for historical/past-year data where TM has no events.
    Tries tour_name first (more specific), then falls back to venueName.
    """
    def _search(params: dict) -> list[dict]:
        try:
            data = setlistfm_get("search/setlists", {**params, "p": 1})
        except Exception as e:
            log.warning(f"Setlist.fm failed ({params}): {e}")
            return []
        seen: set[str] = set()
        artists: list[dict] = []
        for setlist in data.get("setlist", []):
            name = setlist.get("artist", {}).get("name", "").strip()
            if name and name.lower() not in seen:
                seen.add(name.lower())
                artists.append({"name": name, "image_url": None})
        return artists

    # Try tour/event name first if provided (avoids shared-venue collisions)
    if tour_name:
        artists = _search({"tourName": tour_name, "year": year})
        if artists:
            return [{"date": None, "artists": artists, "headliner_count": 0}]

    artists = _search({"venueName": venue_name, "year": year})
    return [{"date": None, "artists": artists, "headliner_count": 0}] if artists else []


# ── Database writes ────────────────────────────────────────────

def resolve_festival_id(supabase: Client, slug: str) -> str | None:
    result = supabase.table("festivals").select("id").eq("slug", slug).execute()
    if not result.data:
        console.log(f"[red]Festival not in DB: {slug} — run festival_scraper.py first")
        return None
    return result.data[0]["id"]


def upsert_artist_record(supabase: Client, name: str, image_url: str | None) -> str | None:
    slug = slugify(name)
    existing = supabase.table("artists").select("id, image_url").eq("slug", slug).execute()
    if existing.data:
        artist_id = existing.data[0]["id"]
        # Update image if we now have one and didn't before
        if image_url and not existing.data[0].get("image_url"):
            supabase.table("artists").update({"image_url": image_url}).eq("id", artist_id).execute()
        return artist_id

    result = supabase.table("artists").insert({
        "slug": slug,
        "name": name,
        "image_url": image_url,
    }).execute()
    if not result.data:
        log.warning(f"Failed to insert artist: {name}")
        return None
    return result.data[0]["id"]


def write_lineup(
    supabase: Client,
    festival_id: str,
    year: int,
    days: list[dict],
    dry_run: bool,
) -> int:
    total = 0
    for day in days:
        event_date = day["date"]
        headliner_count = day["headliner_count"]
        for i, artist_info in enumerate(day["artists"]):
            name = artist_info["name"]
            image_url = artist_info.get("image_url")
            is_headliner = i < headliner_count

            if dry_run:
                flag = "★" if is_headliner else " "
                console.log(f"  {flag} {event_date or 'no-date'} | {name}")
                total += 1
                continue

            artist_id = upsert_artist_record(supabase, name, image_url)
            if not artist_id:
                continue

            try:
                supabase.table("lineups").upsert(
                    {
                        "festival_id": festival_id,
                        "artist_id": artist_id,
                        "year": year,
                        "day": event_date,
                        "is_headliner": is_headliner,
                    },
                    on_conflict="festival_id,artist_id,year",
                ).execute()
                total += 1
            except Exception as e:
                log.warning(f"Lineup upsert failed for {name}: {e}")

            time.sleep(0.03)

    return total


# ── Main orchestration ─────────────────────────────────────────

def process_festival(
    supabase: Client | None,
    slug: str,
    cfg: dict,
    year: int,
    source: str | None,
    dry_run: bool,
) -> None:
    console.log(f"\n[bold cyan]{slug}")

    # 1. Try Ticketmaster first (unless forced to setlistfm)
    days: list[dict] = []
    used_source = ""

    if source != "setlistfm":
        days = fetch_tm_lineup(cfg["ticketmaster_keyword"], year, festival_slug=slug)
        if days:
            used_source = "ticketmaster"
            artist_count = sum(len(d["artists"]) for d in days)
            console.log(f"  [green]Ticketmaster: {len(days)} days · {artist_count} artists")

    # 2. Fall back to Setlist.fm
    if not days and source != "ticketmaster":
        tour_name = cfg.get("setlistfm_tour", "")
        console.log(f"  [yellow]Ticketmaster empty — trying Setlist.fm (venue: {cfg['setlistfm_venue']})")
        days = fetch_setlistfm_lineup(cfg["setlistfm_venue"], year, tour_name=tour_name)
        if days:
            used_source = "setlist.fm"
            artist_count = sum(len(d["artists"]) for d in days)
            console.log(f"  [green]Setlist.fm: {artist_count} artists (no per-day breakdown)")
        else:
            # Also try previous year on setlist.fm for passed festivals
            console.log(f"  [yellow]Setlist.fm {year} empty — trying {year - 1}")
            days = fetch_setlistfm_lineup(cfg["setlistfm_venue"], year - 1, tour_name=tour_name)
            if days:
                used_source = f"setlist.fm ({year - 1})"
                artist_count = sum(len(d["artists"]) for d in days)
                console.log(f"  [green]Setlist.fm {year - 1}: {artist_count} artists")

    if not days:
        console.log(f"  [red]No lineup data found — leaving as TBD")
        return

    if dry_run:
        console.log(f"  [dim]DRY RUN — would write {sum(len(d['artists']) for d in days)} entries via {used_source}")
        # Print first day sample
        sample = days[0]
        for a in sample["artists"][:8]:
            flag = "★" if sample["artists"].index(a) < sample["headliner_count"] else " "
            console.log(f"    {flag} {a['name']}")
        return

    festival_id = resolve_festival_id(supabase, slug)
    if not festival_id:
        return

    n = write_lineup(supabase, festival_id, year, days, dry_run=False)
    console.log(f"  [bold green]✓ {n} lineup entries written ({used_source})")


def main():
    parser = argparse.ArgumentParser(description="Scrape festival lineups into Supabase")
    parser.add_argument("--festival", type=str, help="Single festival slug")
    parser.add_argument("--year", type=int, default=date.today().year)
    parser.add_argument("--source", choices=["ticketmaster", "setlistfm"], help="Force a specific source")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, no DB writes")
    args = parser.parse_args()

    console.log(f"[bold]Festival Lineup Scraper — {args.year}{' (DRY RUN)' if args.dry_run else ''}")

    supabase = None if args.dry_run else get_supabase()

    targets = (
        {args.festival: FESTIVAL_CONFIG[args.festival]}
        if args.festival and args.festival in FESTIVAL_CONFIG
        else FESTIVAL_CONFIG
    )
    if args.festival and args.festival not in FESTIVAL_CONFIG:
        console.log(f"[red]Unknown festival slug: {args.festival}")
        console.log(f"Available: {', '.join(FESTIVAL_CONFIG.keys())}")
        return

    for slug, cfg in track(targets.items(), description="Processing festivals..."):
        try:
            process_festival(supabase, slug, cfg, args.year, args.source, args.dry_run)
        except Exception as e:
            console.log(f"  [red]Error processing {slug}: {e}")
        time.sleep(0.2)  # TM rate limit buffer

    console.log("\n[bold green]Done.")


if __name__ == "__main__":
    main()
