"""
festival_scraper.py
-------------------
Scrapes the Wikipedia list of US music festivals and upserts them into Supabase.

Source: https://en.wikipedia.org/wiki/List_of_music_festivals_in_the_United_States

Run:
    python festival_scraper.py                  # full scrape
    python festival_scraper.py --festival "Lollapalooza"  # single festival

Schedule: Weekly via GitHub Actions (etl_weekly.yml)
"""

import os
import re
import time
import logging
import argparse
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
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/List_of_music_festivals_in_the_United_States"

# Manual enrichment for the top festivals (Phase 1-2 priority list)
# These fill in fields Wikipedia doesn't have (social handles, colors, etc.)
PRIORITY_FESTIVALS = {
    "Lollapalooza": {
        "city": "Chicago",
        "state": "IL",
        "venue": "Grant Park",
        "instagram_handle": "lollapalooza",
        "x_handle": "lollapalooza",
        "accent_color": "#FF4500",
        "tags": ["multi-genre", "outdoor", "annual", "flagship", "urban", "summer", "midwest"],
        "website_url": "https://www.lollapalooza.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Lollapalooza",
    },
    "Coachella": {
        "city": "Indio",
        "state": "CA",
        "venue": "Empire Polo Club",
        "instagram_handle": "coachella",
        "x_handle": "coachella",
        "accent_color": "#00A878",
        "tags": ["multi-genre", "outdoor", "annual", "flagship", "camping", "southwest", "spring"],
        "website_url": "https://www.coachella.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Coachella_Valley_Music_and_Arts_Festival",
    },
    "Electric Daisy Carnival Las Vegas": {
        "city": "Las Vegas",
        "state": "NV",
        "venue": "Las Vegas Motor Speedway",
        "instagram_handle": "electricdaisycarnival",
        "x_handle": "EDC_LasVegas",
        "accent_color": "#FF007F",
        "tags": ["edm", "electronic", "outdoor", "annual", "flagship", "southwest", "summer"],
        "website_url": "https://lasvegas.electricdaisycarnival.com",
    },
    "South by Southwest": {
        "city": "Austin",
        "state": "TX",
        "venue": "Multiple Venues",
        "instagram_handle": "sxsw",
        "x_handle": "sxsw",
        "accent_color": "#E63946",
        "tags": ["multi-genre", "indie", "urban", "annual", "flagship", "southeast", "spring"],
        "website_url": "https://www.sxsw.com",
    },
    "Ultra Music Festival": {
        "city": "Miami",
        "state": "FL",
        "venue": "Bayfront Park",
        "instagram_handle": "ultra",
        "x_handle": "ultra",
        "accent_color": "#00D4FF",
        "tags": ["edm", "electronic", "outdoor", "annual", "flagship", "southeast", "spring"],
        "website_url": "https://ultramusicfestival.com",
    },
    "Governors Ball": {
        "city": "New York",
        "state": "NY",
        "venue": "Flushing Meadows Corona Park",
        "instagram_handle": "governorsballnyc",
        "x_handle": "GovBallNYC",
        "accent_color": "#7B2FBE",
        "tags": ["multi-genre", "outdoor", "annual", "flagship", "urban", "northeast", "summer"],
        "website_url": "https://www.governorsballmusicfestival.com",
    },
}


def get_supabase() -> Client:
    url = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_wikipedia() -> BeautifulSoup:
    console.log("[cyan]Fetching Wikipedia festival list...")
    resp = requests.get(WIKIPEDIA_URL, headers={"User-Agent": "FestivalAnalyzerBot/1.0"}, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def parse_festivals(soup: BeautifulSoup) -> list[dict]:
    """
    Parses the Wikipedia table(s) for US music festivals.
    Returns a list of dicts with festival metadata.
    """
    festivals = []
    tables = soup.find_all("table", class_="wikitable")

    for table in tables:
        rows = table.find_all("tr")[1:]  # skip header
        for row in rows:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
            try:
                name_cell = cells[0]
                name = name_cell.get_text(strip=True)
                if not name:
                    continue

                # Try to extract Wikipedia link for this festival
                wiki_link = name_cell.find("a", href=True)
                wiki_url = f"https://en.wikipedia.org{wiki_link['href']}" if wiki_link else None

                # Try to extract location from subsequent cells
                city, state = None, None
                if len(cells) > 1:
                    location_text = cells[1].get_text(strip=True)
                    parts = [p.strip() for p in location_text.split(",")]
                    if len(parts) >= 2:
                        city = parts[0]
                        state = parts[1][:2].upper() if parts[1] else None

                festival = {
                    "slug": slugify(name),
                    "name": name,
                    "city": city,
                    "state": state,
                    "wikipedia_url": wiki_url,
                    "tags": [],
                    "is_active": True,
                }

                # Merge in priority data if available
                for priority_name, priority_data in PRIORITY_FESTIVALS.items():
                    if priority_name.lower() in name.lower():
                        festival.update(priority_data)
                        break

                festivals.append(festival)
            except Exception as e:
                log.warning(f"Failed to parse row: {e}")
                continue

    console.log(f"[green]Parsed {len(festivals)} festivals from Wikipedia")
    return festivals


def upsert_festivals(supabase: Client, festivals: list[dict]) -> None:
    """Upserts festival records into Supabase."""
    console.log(f"[cyan]Upserting {len(festivals)} festivals...")
    for festival in track(festivals, description="Upserting festivals..."):
        try:
            supabase.table("festivals").upsert(festival, on_conflict="slug").execute()
        except Exception as e:
            log.error(f"Failed to upsert {festival.get('name')}: {e}")
    console.log("[green]Done upserting festivals")


def scrape_single(supabase: Client, festival_name: str) -> None:
    """Upsert a single festival by name from the priority list."""
    name_lower = festival_name.lower()
    match = next(
        (v | {"name": k, "slug": slugify(k)} for k, v in PRIORITY_FESTIVALS.items() if k.lower() == name_lower),
        None
    )
    if not match:
        console.log(f"[red]{festival_name} not found in priority list. Add it to PRIORITY_FESTIVALS first.")
        return
    supabase.table("festivals").upsert(match, on_conflict="slug").execute()
    console.log(f"[green]Upserted: {festival_name}")


def main():
    parser = argparse.ArgumentParser(description="Scrape US music festivals into Supabase")
    parser.add_argument("--festival", type=str, help="Scrape only this festival name")
    parser.add_argument("--priority-only", action="store_true", help="Only upsert PRIORITY_FESTIVALS")
    args = parser.parse_args()

    supabase = get_supabase()

    if args.festival:
        scrape_single(supabase, args.festival)
        return

    if args.priority_only:
        festivals = [
            {"name": k, "slug": slugify(k), **v}
            for k, v in PRIORITY_FESTIVALS.items()
        ]
        upsert_festivals(supabase, festivals)
        return

    soup = fetch_wikipedia()
    festivals = parse_festivals(soup)
    upsert_festivals(supabase, festivals)


if __name__ == "__main__":
    main()
