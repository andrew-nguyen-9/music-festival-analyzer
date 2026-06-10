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
    # ── Big 6 ────────────────────────────────────────────────────
    "Lollapalooza": {
        "city": "Chicago", "state": "IL", "venue": "Grant Park",
        "instagram_handle": "lollapalooza", "x_handle": "lollapalooza",
        "accent_color": "#FF4500",
        "tags": ["multi-genre", "outdoor", "annual", "flagship", "urban", "summer", "midwest"],
        "website_url": "https://www.lollapalooza.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Lollapalooza",
    },
    "Coachella": {
        "city": "Indio", "state": "CA", "venue": "Empire Polo Club",
        "instagram_handle": "coachella", "x_handle": "coachella",
        "accent_color": "#00A878",
        "tags": ["multi-genre", "outdoor", "annual", "flagship", "camping", "southwest", "spring"],
        "website_url": "https://www.coachella.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Coachella_Valley_Music_and_Arts_Festival",
    },
    "Electric Daisy Carnival": {
        "city": "Las Vegas", "state": "NV", "venue": "Las Vegas Motor Speedway",
        "instagram_handle": "electricdaisycarnival", "x_handle": "EDC_LasVegas",
        "accent_color": "#FF007F",
        "tags": ["edm", "electronic", "outdoor", "annual", "flagship", "southwest", "summer"],
        "website_url": "https://lasvegas.electricdaisycarnival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Electric_Daisy_Carnival",
    },
    "South by Southwest": {
        "city": "Austin", "state": "TX", "venue": "Multiple Venues",
        "instagram_handle": "sxsw", "x_handle": "sxsw",
        "accent_color": "#E63946",
        "tags": ["multi-genre", "indie", "urban", "annual", "flagship", "southeast", "spring"],
        "website_url": "https://www.sxsw.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/South_by_Southwest",
    },
    "Outside Lands": {
        "city": "San Francisco", "state": "CA", "venue": "Golden Gate Park",
        "instagram_handle": "outsidelands", "x_handle": "outsidelands",
        "accent_color": "#00A878",
        "tags": ["multi-genre", "outdoor", "annual", "flagship", "west-coast", "summer"],
        "website_url": "https://www.sfoutsidelands.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Outside_Lands_Music_and_Arts_Festival",
    },
    "Ultra Music Festival": {
        "city": "Miami", "state": "FL", "venue": "Bayfront Park",
        "instagram_handle": "ultra", "x_handle": "ultra",
        "accent_color": "#00D4FF",
        "tags": ["edm", "electronic", "outdoor", "annual", "flagship", "southeast", "spring"],
        "website_url": "https://ultramusicfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Ultra_Music_Festival",
    },
    # ── 20 Additional Major Festivals ────────────────────────────
    "Bonnaroo Music and Arts Festival": {
        "city": "Manchester", "state": "TN", "venue": "The Farm",
        "instagram_handle": "bonnaroo", "x_handle": "bonnaroo",
        "accent_color": "#FF7A45",
        "tags": ["multi-genre", "outdoor", "annual", "camping", "southeast", "summer"],
        "website_url": "https://www.bonnaroo.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Bonnaroo_Music_and_Arts_Festival",
    },
    "Austin City Limits Music Festival": {
        "city": "Austin", "state": "TX", "venue": "Zilker Park",
        "instagram_handle": "aclfestival", "x_handle": "aclfestival",
        "accent_color": "#E63946",
        "tags": ["multi-genre", "outdoor", "annual", "urban", "southeast", "fall"],
        "website_url": "https://www.aclfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Austin_City_Limits_Music_Festival",
    },
    "Governors Ball": {
        "city": "New York", "state": "NY", "venue": "Flushing Meadows Corona Park",
        "instagram_handle": "governorsballnyc", "x_handle": "GovBallNYC",
        "accent_color": "#7B2FBE",
        "tags": ["multi-genre", "outdoor", "annual", "urban", "northeast", "summer"],
        "website_url": "https://www.governorsballmusicfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Governors_Ball_Music_Festival",
    },
    "Stagecoach": {
        "city": "Indio", "state": "CA", "venue": "Empire Polo Club",
        "instagram_handle": "stagecoachfest", "x_handle": "stagecoachfest",
        "accent_color": "#F59E0B",
        "tags": ["country", "outdoor", "annual", "camping", "southwest", "spring"],
        "website_url": "https://www.stagecoachfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Stagecoach_Festival",
    },
    "BottleRock Napa Valley": {
        "city": "Napa", "state": "CA", "venue": "Napa Valley Expo",
        "instagram_handle": "bottlerocknapavalley", "x_handle": "BottleRockNapa",
        "accent_color": "#FF4500",
        "tags": ["multi-genre", "outdoor", "annual", "west-coast", "spring"],
        "website_url": "https://www.bottlerocknapavalley.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/BottleRock_Napa_Valley",
    },
    "Rolling Loud": {
        "city": "Miami", "state": "FL", "venue": "Hard Rock Stadium",
        "instagram_handle": "rollingloud", "x_handle": "RollingLoud",
        "accent_color": "#FF007F",
        "tags": ["hip-hop", "outdoor", "annual", "southeast", "summer"],
        "website_url": "https://rollingloud.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Rolling_Loud",
    },
    "Firefly Music Festival": {
        "city": "Dover", "state": "DE", "venue": "The Woodlands",
        "instagram_handle": "fireflyfest", "x_handle": "fireflyfest",
        "accent_color": "#00D4FF",
        "tags": ["multi-genre", "outdoor", "annual", "camping", "northeast", "summer"],
        "website_url": "https://fireflyfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Firefly_Music_Festival",
    },
    "Hangout Music Festival": {
        "city": "Gulf Shores", "state": "AL", "venue": "Gulf Shores Public Beach",
        "instagram_handle": "hangoutfest", "x_handle": "hangoutfest",
        "accent_color": "#00A878",
        "tags": ["multi-genre", "outdoor", "annual", "southeast", "spring"],
        "website_url": "https://www.hangoutmusicfest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Hangout_Music_Festival",
    },
    "New Orleans Jazz & Heritage Festival": {
        "city": "New Orleans", "state": "LA", "venue": "Fair Grounds Race Course",
        "instagram_handle": "nojazzfest", "x_handle": "nojazzfest",
        "accent_color": "#FF7A45",
        "tags": ["jazz", "multi-genre", "outdoor", "annual", "southeast", "spring"],
        "website_url": "https://www.nojazzfest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/New_Orleans_Jazz_%26_Heritage_Festival",
    },
    "Newport Folk Festival": {
        "city": "Newport", "state": "RI", "venue": "Fort Adams State Park",
        "instagram_handle": "newportfolk", "x_handle": "newportfolk",
        "accent_color": "#F59E0B",
        "tags": ["indie", "outdoor", "annual", "northeast", "summer"],
        "website_url": "https://www.newportfolk.org",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Newport_Folk_Festival",
    },
    "Essence Festival of Culture": {
        "city": "New Orleans", "state": "LA", "venue": "Caesars Superdome",
        "instagram_handle": "essencefest", "x_handle": "essencefest",
        "accent_color": "#7B2FBE",
        "tags": ["hip-hop", "r&b", "annual", "southeast", "summer"],
        "website_url": "https://www.essence.com/festival",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Essence_Festival_of_Culture",
    },
    "Life is Beautiful": {
        "city": "Las Vegas", "state": "NV", "venue": "Downtown Las Vegas",
        "instagram_handle": "lifeisbeautiful", "x_handle": "lifeisbeautiful",
        "accent_color": "#00D4FF",
        "tags": ["multi-genre", "outdoor", "annual", "urban", "southwest", "fall"],
        "website_url": "https://lifeisbeautiful.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Life_Is_Beautiful_festival",
    },
    "Pitchfork Music Festival": {
        "city": "Chicago", "state": "IL", "venue": "Union Park",
        "instagram_handle": "pitchforkfest", "x_handle": "pitchforkfest",
        "accent_color": "#E63946",
        "tags": ["indie", "outdoor", "annual", "urban", "midwest", "summer"],
        "website_url": "https://pitchforkmusicfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Pitchfork_Music_Festival",
    },
    "Hard Summer": {
        "city": "Los Angeles", "state": "CA", "venue": "Auto Club Speedway",
        "instagram_handle": "hardfest", "x_handle": "hardfest",
        "accent_color": "#FF007F",
        "tags": ["edm", "electronic", "outdoor", "annual", "west-coast", "summer"],
        "website_url": "https://www.hardfest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Hard_Summer",
    },
    "Ohana Festival": {
        "city": "Dana Point", "state": "CA", "venue": "Doheny State Beach",
        "instagram_handle": "ohanafest", "x_handle": "ohanafest",
        "accent_color": "#00A878",
        "tags": ["rock", "indie", "outdoor", "annual", "west-coast", "fall"],
        "website_url": "https://ohanafest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Ohana_Festival",
    },
    "Summer Smash": {
        "city": "Chicago", "state": "IL", "venue": "Douglass Park",
        "instagram_handle": "summersmashfest", "x_handle": "summersmashfest",
        "accent_color": "#FF4500",
        "tags": ["hip-hop", "outdoor", "annual", "urban", "midwest", "summer"],
        "website_url": "https://www.summersmash.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Summer_Smash",
    },
    "When We Were Young": {
        "city": "Las Vegas", "state": "NV", "venue": "Las Vegas Festival Grounds",
        "instagram_handle": "wwwyfestival", "x_handle": "wwwyfestival",
        "accent_color": "#7B2FBE",
        "tags": ["rock", "outdoor", "annual", "southwest", "fall"],
        "website_url": "https://www.whenwewereyoungfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/When_We_Were_Young_(festival)",
    },
    "Day N Vegas": {
        "city": "Las Vegas", "state": "NV", "venue": "Las Vegas Festival Grounds",
        "instagram_handle": "daynvegas", "x_handle": "daynvegas",
        "accent_color": "#FF007F",
        "tags": ["hip-hop", "outdoor", "annual", "southwest", "fall"],
        "website_url": "https://daynvegas.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Day_N_Vegas",
    },
    "Voodoo Fest": {
        "city": "New Orleans", "state": "LA", "venue": "City Park",
        "instagram_handle": "voodoofest", "x_handle": "voodoofest",
        "accent_color": "#7B2FBE",
        "tags": ["multi-genre", "outdoor", "annual", "southeast", "fall"],
        "website_url": "https://voodoofest.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Voodoo_Experience",
    },
    "Electric Forest": {
        "city": "Rothbury", "state": "MI", "venue": "Double JJ Resort",
        "instagram_handle": "electricforest", "x_handle": "electricforest",
        "accent_color": "#00A878",
        "tags": ["edm", "electronic", "outdoor", "annual", "camping", "midwest", "summer"],
        "website_url": "https://electricforestfestival.com",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Electric_Forest_Festival",
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
