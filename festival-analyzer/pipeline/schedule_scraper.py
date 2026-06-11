"""
schedule_scraper.py
--------------------
Fetches full festival schedules (artist × stage × day × time) from multiple sources:

  1. Ticketmaster Discovery API  — day-by-day set times when published
  2. Songkick API                — structured set-time data per festival
  3. Festival official website   — scrape the /schedule or /lineup page
  4. Claude Vision OCR           — last resort: if festival posts a schedule image,
                                   download it and ask Claude to extract the data

Writes to the lineups table: stage, day, set_time_start, set_time_end, is_headliner.

Run:
    python schedule_scraper.py --festival lollapalooza --year 2026
    python schedule_scraper.py --festival lollapalooza --dry-run
    python schedule_scraper.py --source ocr --festival lollapalooza
    python schedule_scraper.py  # all festivals

Schedule: Daily GitHub Actions (etl_daily.yml) — idempotent upserts
"""

import os
import re
import base64
import time
import json
import logging
import argparse
from datetime import date, datetime
from io import BytesIO
from slugify import slugify
from dotenv import load_dotenv

import requests
import anthropic
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.console import Console
from rich.progress import track

load_dotenv()
console = Console()
log = logging.getLogger(__name__)


# ── Festival schedule source configuration ────────────────────

SCHEDULE_CONFIG: dict[str, dict] = {
    "lollapalooza": {
        "schedule_url": "https://www.lollapalooza.com/lineup/",
        "songkick_id": 4411,
        "tm_keyword": "Lollapalooza",
        "schedule_image_patterns": ["schedule", "lineup", "grid"],
    },
    "coachella": {
        "schedule_url": "https://www.coachella.com/lineup",
        "songkick_id": 11129,
        "tm_keyword": "Coachella Valley Music",
    },
    "bonnaroo-music-and-arts-festival": {
        "schedule_url": "https://www.bonnaroo.com/lineup/",
        "songkick_id": 4418,
        "tm_keyword": "Bonnaroo",
    },
    "outside-lands": {
        "schedule_url": "https://www.sfoutsidelands.com/lineup/",
        "songkick_id": 4587,
        "tm_keyword": "Outside Lands",
    },
    "governors-ball": {
        "schedule_url": "https://www.governorsballmusicfestival.com/lineup/",
        "songkick_id": 1180209,
        "tm_keyword": "Governors Ball",
    },
    "austin-city-limits-music-festival": {
        "schedule_url": "https://www.aclfestival.com/lineup/",
        "songkick_id": 4416,
        "tm_keyword": "Austin City Limits Music Festival",
    },
    "electric-daisy-carnival": {
        "schedule_url": "https://lasvegas.electricdaisycarnival.com/lineup/",
        "songkick_id": 4424,
        "tm_keyword": "Electric Daisy Carnival",
    },
    "stagecoach": {
        "schedule_url": "https://www.stagecoachfestival.com/lineup/",
        "songkick_id": 4426,
        "tm_keyword": "Stagecoach Festival",
    },
    "ultra-music-festival": {
        "schedule_url": "https://ultramusicfestival.com/lineup/",
        "songkick_id": 4423,
        "tm_keyword": "Ultra Music Festival",
    },
    "electric-forest": {
        "schedule_url": "https://electricforestfestival.com/lineup/",
        "songkick_id": 4428,
        "tm_keyword": "Electric Forest",
    },
    "firefly-music-festival": {
        "schedule_url": "https://fireflyfestival.com/lineup/",
        "songkick_id": 4429,
        "tm_keyword": "Firefly Music Festival",
    },
    "rolling-loud": {
        "schedule_url": "https://rollingloud.com/lineup/",
        "songkick_id": None,
        "tm_keyword": "Rolling Loud",
    },
}


# ── Supabase + API clients ────────────────────────────────────

def get_supabase() -> Client:
    return create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def get_anthropic() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


# ── Ticketmaster schedule source ──────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def fetch_tm_schedule(keyword: str, year: int) -> list[dict]:
    """
    Fetches per-day/per-set schedules from Ticketmaster.
    Returns list of: { artist, stage, day, set_start, set_end, is_headliner }
    """
    api_key = os.environ.get("TICKETMASTER_API_KEY", "")
    if not api_key:
        return []

    resp = requests.get(
        "https://app.ticketmaster.com/discovery/v2/events.json",
        params={
            "keyword": keyword,
            "classificationName": "Music",
            "countryCode": "US",
            "size": 50,
            "sort": "date,asc",
            "apikey": api_key,
        },
        timeout=15,
    )
    if resp.status_code == 401:
        return []
    resp.raise_for_status()

    entries: list[dict] = []
    events = resp.json().get("_embedded", {}).get("events", [])

    for event in events:
        event_date = event.get("dates", {}).get("start", {}).get("localDate", "")
        if not event_date or not event_date.startswith(str(year)):
            continue

        start_time = event.get("dates", {}).get("start", {}).get("localTime")
        end_time = None

        for att in event.get("_embedded", {}).get("attractions", []):
            name = att.get("name", "").strip()
            if not name or keyword.lower() in name.lower():
                continue
            stage = (att.get("classifications") or [{}])[0].get("subType", {}).get("name")
            entries.append({
                "artist": name,
                "stage": stage,
                "day": event_date,
                "set_start": start_time,
                "set_end": end_time,
                "is_headliner": False,
            })

    return entries


# ── Songkick schedule source ──────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def fetch_songkick_schedule(songkick_id: int, year: int) -> list[dict]:
    """
    Fetches festival performances from the Songkick API.
    Requires SONGKICK_API_KEY env var.
    """
    api_key = os.environ.get("SONGKICK_API_KEY", "")
    if not api_key or not songkick_id:
        return []

    try:
        resp = requests.get(
            f"https://api.songkick.com/api/3.0/events/{songkick_id}/performances.json",
            params={"apikey": api_key},
            timeout=15,
        )
        if resp.status_code in (401, 403, 404):
            return []
        resp.raise_for_status()
        data = resp.json()

        entries: list[dict] = []
        for perf in data.get("resultsPage", {}).get("results", {}).get("performance", []):
            artist = perf.get("artist", {}).get("displayName", "").strip()
            if not artist:
                continue
            billing = perf.get("billingIndex", 99)
            entries.append({
                "artist": artist,
                "stage": perf.get("stage", {}).get("name") if perf.get("stage") else None,
                "day": perf.get("event", {}).get("start", {}).get("date"),
                "set_start": perf.get("event", {}).get("start", {}).get("time"),
                "set_end": None,
                "is_headliner": billing <= 3,
            })
        return entries
    except Exception as e:
        log.warning(f"Songkick failed (id={songkick_id}): {e}")
        return []


# ── Web scrape for schedule image + Claude OCR ────────────────

def find_schedule_image(url: str) -> str | None:
    """
    Fetches a festival's schedule page and looks for an image that contains
    the schedule grid (often posted as a PNG or JPG).
    """
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        soup = __import__("bs4").BeautifulSoup(resp.text, "html.parser")

        schedule_keywords = ["schedule", "lineup", "grid", "timetable", "set-times"]

        for img in soup.find_all("img"):
            src = img.get("src", "") or img.get("data-src", "")
            alt = (img.get("alt", "") or "").lower()
            if any(kw in src.lower() or kw in alt for kw in schedule_keywords):
                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    src = f"{parsed.scheme}://{parsed.netloc}{src}"
                return src
        return None
    except Exception as e:
        log.warning(f"Schedule page fetch failed for {url}: {e}")
        return None


def ocr_schedule_image(image_url: str, festival_name: str, year: int) -> list[dict]:
    """
    Downloads a schedule image and asks Claude to extract the lineup.
    Returns list of: { artist, stage, day, set_start, set_end, is_headliner }
    """
    try:
        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()

        content_type = img_resp.headers.get("content-type", "image/jpeg")
        img_b64 = base64.standard_b64encode(img_resp.content).decode("utf-8")

        client = get_anthropic()
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": content_type,
                            "data": img_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": f"""This is a schedule/lineup image for {festival_name} {year}.
Extract ALL artists from this image into a JSON array.

For each artist, extract:
- "artist": the artist name (string)
- "stage": stage name if visible (string or null)
- "day": date string in YYYY-MM-DD if visible, else null
- "set_start": start time in HH:MM 24h format if visible, else null
- "set_end": end time in HH:MM 24h format if visible, else null
- "is_headliner": true if the artist appears to be a headliner (large font, top billing)

Return ONLY valid JSON: {{ "artists": [ ... ] }}
No other text.""",
                    },
                ],
            }],
        )

        response_text = message.content[0].text.strip()
        # Extract JSON even if there's surrounding text
        json_match = re.search(r'\{.*"artists".*\}', response_text, re.DOTALL)
        if not json_match:
            log.warning(f"Claude OCR returned non-JSON for {festival_name}")
            return []

        data = json.loads(json_match.group())
        entries = data.get("artists", [])
        console.log(f"[green]OCR extracted {len(entries)} artists from {festival_name} schedule image")
        return entries

    except Exception as e:
        log.error(f"Claude OCR failed for {festival_name}: {e}")
        return []


# ── Database helpers ──────────────────────────────────────────

def upsert_artist_record(supabase: Client, name: str) -> str | None:
    slug = slugify(name)
    existing = supabase.table("artists").select("id").eq("slug", slug).execute()
    if existing.data:
        return existing.data[0]["id"]
    result = supabase.table("artists").insert({"slug": slug, "name": name}).execute()
    return result.data[0]["id"] if result.data else None


def write_schedule(
    supabase: Client,
    festival_id: str,
    year: int,
    entries: list[dict],
    dry_run: bool,
) -> int:
    total = 0
    for entry in entries:
        name = entry.get("artist", "").strip()
        if not name:
            continue

        if dry_run:
            flag = "★" if entry.get("is_headliner") else " "
            t = entry.get("set_start") or "?"
            stage = entry.get("stage") or "?"
            console.log(f"  {flag} {entry.get('day') or '?'} {t:8s} | {stage:20s} | {name}")
            total += 1
            continue

        artist_id = upsert_artist_record(supabase, name)
        if not artist_id:
            continue

        payload = {
            "festival_id": festival_id,
            "artist_id": artist_id,
            "year": year,
            "day": entry.get("day"),
            "stage": entry.get("stage"),
            "set_time_start": entry.get("set_start"),
            "set_time_end": entry.get("set_end"),
            "is_headliner": bool(entry.get("is_headliner", False)),
        }
        try:
            supabase.table("lineups").upsert(
                payload,
                on_conflict="festival_id,artist_id,year",
            ).execute()
            total += 1
        except Exception as e:
            log.warning(f"Lineup upsert failed for {name}: {e}")
        time.sleep(0.02)

    return total


# ── Main orchestration ────────────────────────────────────────

def process_festival(
    supabase: Client | None,
    slug: str,
    cfg: dict,
    year: int,
    source: str | None,
    dry_run: bool,
) -> None:
    console.log(f"\n[bold cyan]{slug}")

    entries: list[dict] = []
    used_source = ""

    # 1. Ticketmaster
    if source in (None, "ticketmaster") and cfg.get("tm_keyword"):
        entries = fetch_tm_schedule(cfg["tm_keyword"], year)
        if entries:
            used_source = "ticketmaster"
            console.log(f"  [green]Ticketmaster: {len(entries)} entries")

    # 2. Songkick
    if not entries and source in (None, "songkick") and cfg.get("songkick_id"):
        entries = fetch_songkick_schedule(cfg["songkick_id"], year)
        if entries:
            used_source = "songkick"
            console.log(f"  [green]Songkick: {len(entries)} entries")

    # 3. OCR fallback
    if not entries and source in (None, "ocr") and cfg.get("schedule_url"):
        console.log(f"  [yellow]Trying schedule page OCR...")
        img_url = find_schedule_image(cfg["schedule_url"])
        if img_url:
            console.log(f"  [cyan]Found schedule image: {img_url[:80]}...")
            entries = ocr_schedule_image(img_url, slug, year)
            if entries:
                used_source = "ocr"

    if not entries:
        console.log(f"  [red]No schedule data found for {slug} {year}")
        return

    if dry_run:
        console.log(f"  [dim]DRY RUN — {len(entries)} entries via {used_source}")
        for e in entries[:5]:
            console.log(f"    {e.get('day') or '?'} {e.get('set_start') or '?':8s} | {e.get('stage') or '?':20s} | {e.get('artist')}")
        return

    festival_result = supabase.table("festivals").select("id").eq("slug", slug).execute()
    if not festival_result.data:
        console.log(f"  [red]Festival not in DB: {slug}")
        return
    festival_id = festival_result.data[0]["id"]

    n = write_schedule(supabase, festival_id, year, entries, dry_run=False)
    console.log(f"  [bold green]✓ {n} schedule entries written ({used_source})")


def main():
    parser = argparse.ArgumentParser(description="Scrape festival schedules with set times")
    parser.add_argument("--festival", type=str, help="Festival slug")
    parser.add_argument("--year", type=int, default=date.today().year)
    parser.add_argument("--source", choices=["ticketmaster", "songkick", "ocr"],
                        help="Force a specific source")
    parser.add_argument("--dry-run", action="store_true", help="No DB writes, just print")
    args = parser.parse_args()

    console.log(f"[bold]Schedule Scraper — {args.year}{' (DRY RUN)' if args.dry_run else ''}")
    supabase = None if args.dry_run else get_supabase()

    if args.festival:
        if args.festival not in SCHEDULE_CONFIG:
            console.log(f"[red]Unknown festival: {args.festival}")
            console.log(f"Available: {', '.join(SCHEDULE_CONFIG.keys())}")
            return
        targets = {args.festival: SCHEDULE_CONFIG[args.festival]}
    else:
        targets = SCHEDULE_CONFIG

    for slug, cfg in track(targets.items(), description="Processing..."):
        try:
            process_festival(supabase, slug, cfg, args.year, args.source, args.dry_run)
        except Exception as e:
            console.log(f"  [red]Error processing {slug}: {e}")
        time.sleep(0.5)

    console.log("\n[bold green]Done.")


if __name__ == "__main__":
    main()
