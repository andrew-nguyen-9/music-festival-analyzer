"""
festival_dates_enricher.py
--------------------------
Pulls start/end dates for festivals from multiple sources:
  1. Ticketmaster Discovery API  (upcoming confirmed events)
  2. Wikipedia infobox scraping  (announced or historical dates)
  3. Historical estimates        (based on typical month/week patterns)

Sets start_date, end_date, and dates_estimated in Supabase.
For festivals not yet announced, estimates dates based on the festival's
typical calendar slot and flags them as estimated so the UI can show "~".

Run:
    python festival_dates_enricher.py                    # all festivals
    python festival_dates_enricher.py --festival lollapalooza
    python festival_dates_enricher.py --dry-run
    python festival_dates_enricher.py --estimates-only   # skip confirmed, only fill TBD

Schedule: Weekly via GitHub Actions
"""

import os
import re
import time
import logging
import argparse
from datetime import date, timedelta
from calendar import monthcalendar, THURSDAY
from slugify import slugify
from dotenv import load_dotenv

import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.console import Console
from rich.progress import track

load_dotenv()
console = Console()
log = logging.getLogger(__name__)


# ── Historical date patterns ───────────────────────────────────
# Each entry describes when the festival *typically* occurs.
# month: 1-based calendar month
# week_of_month: 1=first, 2=second, 3=third, 4=fourth, -1=last
# day_of_week: 0=Mon ... 4=Thu ... 5=Fri ... 6=Sun
# duration_days: total days the festival runs

FESTIVAL_PATTERNS: dict[str, dict] = {
    "lollapalooza": {
        "month": 8, "week_of_month": 1, "day_of_week": 4, "duration_days": 4,
        "description": "First weekend of August (Thu–Sun)",
    },
    "coachella": {
        "month": 4, "week_of_month": 2, "day_of_week": 4, "duration_days": 10,
        "description": "Weekends 2 & 3 of April (two identical weekends)",
    },
    "electric-daisy-carnival": {
        "month": 5, "week_of_month": 3, "day_of_week": 4, "duration_days": 3,
        "description": "Third weekend of May (Fri–Sun)",
    },
    "south-by-southwest": {
        "month": 3, "week_of_month": 2, "day_of_week": 4, "duration_days": 10,
        "description": "Mid-March (10 days spanning two weekends)",
    },
    "outside-lands": {
        "month": 8, "week_of_month": 1, "day_of_week": 4, "duration_days": 3,
        "description": "First weekend of August (Fri–Sun)",
    },
    "ultra-music-festival": {
        "month": 3, "week_of_month": 3, "day_of_week": 4, "duration_days": 3,
        "description": "Third weekend of March (Fri–Sun)",
    },
    "bonnaroo-music-and-arts-festival": {
        "month": 6, "week_of_month": 2, "day_of_week": 3, "duration_days": 4,
        "description": "Second weekend of June (Thu–Sun)",
    },
    "austin-city-limits-music-festival": {
        "month": 10, "week_of_month": 1, "day_of_week": 4, "duration_days": 10,
        "description": "First two weekends of October (Fri–Sun, twice)",
    },
    "governors-ball": {
        "month": 6, "week_of_month": 2, "day_of_week": 4, "duration_days": 3,
        "description": "Second weekend of June (Fri–Sun)",
    },
    "stagecoach": {
        "month": 4, "week_of_month": 4, "day_of_week": 4, "duration_days": 3,
        "description": "Last weekend of April (Fri–Sun)",
    },
    "bottlerock-napa-valley": {
        "month": 5, "week_of_month": 4, "day_of_week": 4, "duration_days": 3,
        "description": "Last weekend of May (Fri–Sun)",
    },
    "rolling-loud": {
        "month": 7, "week_of_month": 3, "day_of_week": 4, "duration_days": 3,
        "description": "Third weekend of July (Fri–Sun)",
    },
    "firefly-music-festival": {
        "month": 6, "week_of_month": 3, "day_of_week": 3, "duration_days": 4,
        "description": "Third weekend of June (Thu–Sun)",
    },
    "hangout-music-festival": {
        "month": 5, "week_of_month": 3, "day_of_week": 4, "duration_days": 3,
        "description": "Third weekend of May (Fri–Sun)",
    },
    "new-orleans-jazz-heritage-festival": {
        "month": 4, "week_of_month": 4, "day_of_week": 4, "duration_days": 10,
        "description": "Last weekend of April + first weekend of May",
    },
    "newport-folk-festival": {
        "month": 7, "week_of_month": 4, "day_of_week": 4, "duration_days": 3,
        "description": "Last weekend of July (Fri–Sun)",
    },
    "essence-festival-of-culture": {
        "month": 7, "week_of_month": 1, "day_of_week": 3, "duration_days": 4,
        "description": "4th of July weekend",
    },
    "life-is-beautiful": {
        "month": 9, "week_of_month": 3, "day_of_week": 4, "duration_days": 3,
        "description": "Third weekend of September (Fri–Sun)",
    },
    "pitchfork-music-festival": {
        "month": 7, "week_of_month": 2, "day_of_week": 4, "duration_days": 3,
        "description": "Second weekend of July (Fri–Sun)",
    },
    "hard-summer": {
        "month": 8, "week_of_month": 1, "day_of_week": 5, "duration_days": 2,
        "description": "First weekend of August (Sat–Sun)",
    },
    "ohana-festival": {
        "month": 9, "week_of_month": 3, "day_of_week": 4, "duration_days": 3,
        "description": "Third weekend of September (Fri–Sun)",
    },
    "summer-smash": {
        "month": 6, "week_of_month": 3, "day_of_week": 4, "duration_days": 3,
        "description": "Third weekend of June (Fri–Sun)",
    },
    "when-we-were-young": {
        "month": 10, "week_of_month": 4, "day_of_week": 5, "duration_days": 2,
        "description": "Last weekend of October (Sat–Sun)",
    },
    "electric-forest": {
        "month": 6, "week_of_month": 4, "day_of_week": 3, "duration_days": 4,
        "description": "Last weekend of June (Thu–Sun)",
    },
    "voodoo-fest": {
        "month": 10, "week_of_month": 4, "day_of_week": 5, "duration_days": 3,
        "description": "Halloween weekend (Fri–Sun)",
    },
    "day-n-vegas": {
        "month": 11, "week_of_month": 1, "day_of_week": 4, "duration_days": 3,
        "description": "First weekend of November (Fri–Sun)",
    },
    "burning-man": {
        "month": 8, "week_of_month": -1, "day_of_week": 0, "duration_days": 9,
        "description": "Late August into Labor Day weekend",
    },
    "music-midtown": {
        "month": 9, "week_of_month": 2, "day_of_week": 5, "duration_days": 2,
        "description": "Second weekend of September (Sat–Sun)",
    },
    "acl-fest": {
        "month": 10, "week_of_month": 1, "day_of_week": 4, "duration_days": 10,
        "description": "First two weekends of October",
    },
    "kaaboo": {
        "month": 9, "week_of_month": 2, "day_of_week": 4, "duration_days": 3,
        "description": "Second weekend of September",
    },
    "lockn": {
        "month": 8, "week_of_month": 3, "day_of_week": 3, "duration_days": 4,
        "description": "Third weekend of August (Thu–Sun)",
    },
    "shaky-knees-music-festival": {
        "month": 5, "week_of_month": 1, "day_of_week": 4, "duration_days": 3,
        "description": "First weekend of May (Fri–Sun)",
    },
    "jazz-fest": {
        "month": 4, "week_of_month": 4, "day_of_week": 4, "duration_days": 10,
        "description": "Last weekend of April + first weekend of May",
    },
    "forecastle-festival": {
        "month": 7, "week_of_month": 2, "day_of_week": 4, "duration_days": 3,
        "description": "Second weekend of July (Fri–Sun)",
    },
    "chicago-blues-festival": {
        "month": 6, "week_of_month": 1, "day_of_week": 4, "duration_days": 3,
        "description": "First weekend of June (Fri–Sun)",
    },
    "north-coast-music-festival": {
        "month": 8, "week_of_month": 4, "day_of_week": 5, "duration_days": 3,
        "description": "Last weekend of August (Fri–Sun)",
    },
}


# ── Date calculation helpers ───────────────────────────────────

def nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """
    Returns the n-th occurrence of `weekday` (0=Mon..6=Sun) in the given month/year.
    n=-1 means the last occurrence.
    """
    cal = monthcalendar(year, month)
    # Filter weeks that contain the target weekday
    days = [week[weekday] for week in cal if week[weekday] != 0]
    if n == -1:
        idx = -1
    else:
        idx = n - 1
    return date(year, month, days[idx])


def estimate_dates(slug: str, year: int) -> tuple[date, date] | None:
    """Return estimated (start_date, end_date) for a festival in a given year."""
    pattern = FESTIVAL_PATTERNS.get(slug)
    if not pattern:
        return None
    try:
        start = nth_weekday_of_month(year, pattern["month"], pattern["day_of_week"], pattern["week_of_month"])
        end = start + timedelta(days=pattern["duration_days"] - 1)
        return start, end
    except (IndexError, ValueError):
        return None


# ── Wikipedia date scraping ────────────────────────────────────

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_wiki_dates(wikipedia_url: str) -> tuple[date, date] | None:
    """Scrape start/end dates from a festival's Wikipedia infobox."""
    if not wikipedia_url:
        return None
    try:
        resp = requests.get(
            wikipedia_url,
            headers={"User-Agent": "FestivalAnalyzerBot/1.0"},
            timeout=15,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for infobox date rows
        for row in soup.select("table.infobox tr"):
            header = row.find("th")
            data = row.find("td")
            if not header or not data:
                continue
            header_text = header.get_text(strip=True).lower()
            if "date" not in header_text and "founded" not in header_text and "held" not in header_text:
                continue

            text = data.get_text(separator=" ", strip=True)
            dates = _parse_date_text(text)
            if dates:
                return dates

        return None
    except Exception as e:
        log.warning(f"Wikipedia date scrape failed for {wikipedia_url}: {e}")
        return None


def _parse_date_text(text: str) -> tuple[date, date] | None:
    """
    Tries to extract a date range from strings like:
    "August 1–4, 2026", "April 11 – 20, 2025", "May 22, 2026", etc.
    Returns (start_date, end_date) or None.
    """
    current_year = date.today().year

    # Try "Month D–D, YYYY" or "Month D – D, YYYY"
    m = re.search(
        r"(\w+)\s+(\d{1,2})\s*[–—-]\s*(\d{1,2}),?\s*(\d{4})",
        text, re.IGNORECASE
    )
    if m:
        month_name, start_day, end_day, year = m.groups()
        month = MONTH_MAP.get(month_name.lower())
        if month:
            try:
                return (
                    date(int(year), month, int(start_day)),
                    date(int(year), month, int(end_day)),
                )
            except ValueError:
                pass

    # Try "Month D, YYYY – Month D, YYYY"
    m = re.search(
        r"(\w+)\s+(\d{1,2}),?\s*(\d{4})\s*[–—-]\s*(\w+)\s+(\d{1,2}),?\s*(\d{4})",
        text, re.IGNORECASE
    )
    if m:
        sm, sd, sy, em, ed, ey = m.groups()
        smonth = MONTH_MAP.get(sm.lower())
        emonth = MONTH_MAP.get(em.lower())
        if smonth and emonth:
            try:
                return (
                    date(int(sy), smonth, int(sd)),
                    date(int(ey), emonth, int(ed)),
                )
            except ValueError:
                pass

    # Single date "Month D, YYYY"
    m = re.search(r"(\w+)\s+(\d{1,2}),\s*(\d{4})", text, re.IGNORECASE)
    if m:
        month_name, day, year = m.groups()
        month = MONTH_MAP.get(month_name.lower())
        if month:
            try:
                d = date(int(year), month, int(day))
                return d, d
            except ValueError:
                pass

    return None


# ── Ticketmaster date lookup ───────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def fetch_tm_dates(keyword: str, year: int) -> tuple[date, date] | None:
    """Queries Ticketmaster for the festival event and extracts its date range."""
    try:
        params = {
            "keyword": keyword,
            "classificationName": "Music",
            "countryCode": "US",
            "size": 20,
            "sort": "date,asc",
            "apikey": os.environ.get("TICKETMASTER_API_KEY", ""),
        }
        if not params["apikey"]:
            return None

        resp = requests.get(
            "https://app.ticketmaster.com/discovery/v2/events.json",
            params=params, timeout=15
        )
        if resp.status_code == 401:
            return None
        resp.raise_for_status()
        data = resp.json()

        events = data.get("_embedded", {}).get("events", [])
        dates_found: list[date] = []

        for event in events:
            local_date = event.get("dates", {}).get("start", {}).get("localDate")
            end_date = event.get("dates", {}).get("end", {}).get("localDate") or local_date
            if local_date and str(year) in local_date:
                try:
                    dates_found.append(date.fromisoformat(local_date))
                    if end_date and end_date != local_date:
                        dates_found.append(date.fromisoformat(end_date))
                except ValueError:
                    pass

        if dates_found:
            return min(dates_found), max(dates_found)
    except Exception as e:
        log.warning(f"TM date lookup failed for {keyword}: {e}")
    return None


# ── Main enrichment logic ──────────────────────────────────────

def enrich_festival_dates(
    supabase: Client,
    festival: dict,
    year: int,
    dry_run: bool,
    estimates_only: bool,
) -> None:
    slug = festival["slug"]
    name = festival["name"]
    wiki_url = festival.get("wikipedia_url", "")
    current_start = festival.get("start_date")

    # Skip if already has confirmed dates and not forcing
    if current_start and not estimates_only:
        console.log(f"[dim]{name}: already has dates ({current_start}) — skipping")
        return

    # 1. Try Ticketmaster for live confirmed dates
    tm_key_map = {
        "lollapalooza": "Lollapalooza",
        "coachella": "Coachella Valley Music",
        "electric-daisy-carnival": "Electric Daisy Carnival Las Vegas",
        "bonnaroo-music-and-arts-festival": "Bonnaroo",
        "governors-ball": "Governors Ball",
        "outside-lands": "Outside Lands",
        "austin-city-limits-music-festival": "Austin City Limits Music Festival",
        "stagecoach": "Stagecoach Festival",
        "bottlerock-napa-valley": "BottleRock Napa",
    }
    confirmed: tuple[date, date] | None = None

    if not estimates_only and slug in tm_key_map:
        confirmed = fetch_tm_dates(tm_key_map[slug], year)
        if confirmed:
            console.log(f"[green]{name}: TM confirmed {confirmed[0]} – {confirmed[1]}")

    # 2. Try Wikipedia scraping
    if not confirmed and wiki_url:
        confirmed = fetch_wiki_dates(wiki_url)
        if confirmed:
            # Only keep if it's for the right year
            if confirmed[0].year == year:
                console.log(f"[green]{name}: Wikipedia confirmed {confirmed[0]} – {confirmed[1]}")
            else:
                confirmed = None

    # 3. Fall back to historical estimate
    estimated = False
    if not confirmed:
        est = estimate_dates(slug, year)
        if est:
            confirmed = est
            estimated = True
            console.log(f"[yellow]{name}: estimated {confirmed[0]} – {confirmed[1]}  ({FESTIVAL_PATTERNS[slug]['description']})")
        else:
            console.log(f"[red]{name}: no date data available")
            return

    if dry_run:
        flag = "~" if estimated else "✓"
        console.log(f"  [{flag}] {name}: {confirmed[0]} – {confirmed[1]}")
        return

    try:
        supabase.table("festivals").update({
            "start_date": confirmed[0].isoformat(),
            "end_date": confirmed[1].isoformat(),
            "dates_estimated": estimated,
        }).eq("id", festival["id"]).execute()
    except Exception as e:
        log.error(f"Failed to update dates for {name}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Enrich festival dates from TM, Wikipedia, and historical patterns")
    parser.add_argument("--festival", type=str, help="Festival slug to process")
    parser.add_argument("--year", type=int, default=date.today().year)
    parser.add_argument("--dry-run", action="store_true", help="No DB writes")
    parser.add_argument("--estimates-only", action="store_true", help="Only fill in missing dates with estimates")
    args = parser.parse_args()

    supabase = get_supabase()

    if args.festival:
        result = supabase.table("festivals").select("*").eq("slug", args.festival).execute()
        festivals = result.data
    else:
        result = supabase.table("festivals").select("*").eq("is_active", True).order("name").execute()
        festivals = result.data

    console.log(f"[bold]Festival Date Enricher — {args.year}{' (DRY RUN)' if args.dry_run else ''}")
    console.log(f"[cyan]Processing {len(festivals)} festivals...")

    for festival in track(festivals, description="Enriching dates..."):
        enrich_festival_dates(supabase, festival, args.year, args.dry_run, args.estimates_only)
        time.sleep(0.3)

    console.log("[bold green]Done.")


def get_supabase() -> Client:
    return create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


if __name__ == "__main__":
    main()
