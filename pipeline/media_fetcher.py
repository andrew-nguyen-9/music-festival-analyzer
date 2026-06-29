"""
media_fetcher.py
----------------
Fetches festival photography from the Unsplash API and stores
URLs + attribution in the media table.

Run:
    python media_fetcher.py                      # all active festivals
    python media_fetcher.py --festival lollapalooza

Schedule: Daily via GitHub Actions (etl_daily.yml)
"""

import os
import logging
import argparse
from dotenv import load_dotenv

import requests
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.console import Console

load_dotenv()
console = Console()
log = logging.getLogger(__name__)

UNSPLASH_BASE = "https://api.unsplash.com"

# Map festival slug → search query for best Unsplash results
FESTIVAL_QUERIES = {
    "lollapalooza": "lollapalooza music festival chicago crowd",
    "coachella": "coachella valley music arts festival crowd",
    "electric-daisy-carnival-las-vegas": "EDC electric daisy carnival night festival",
    "south-by-southwest": "SXSW austin music festival street",
    "ultra-music-festival": "ultra music festival miami stage",
    "governors-ball": "governors ball music festival new york",
}

# Map festival slug → city-image search, used for the festival HERO background.
# Each festival shows a city image (not a generic crowd shot) as its hero.
CITY_QUERIES = {
    "lollapalooza": "chicago skyline downtown",
    "coachella": "palm springs california desert",
    "electric-daisy-carnival-las-vegas": "las vegas skyline night",
    "south-by-southwest": "austin texas skyline",
    "ultra-music-festival": "miami skyline downtown",
    "governors-ball": "new york city skyline",
}

DEFAULT_QUERY = "{name} music festival concert"
DEFAULT_CITY_QUERY = "{city} city skyline"
PHOTOS_PER_FESTIVAL = 12


def get_supabase() -> Client:
    return create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def fetch_unsplash_photos(query: str, count: int = 12) -> list[dict]:
    resp = requests.get(
        f"{UNSPLASH_BASE}/search/photos",
        params={
            "query": query,
            "per_page": count,
            "orientation": "landscape",
            "content_filter": "high",
        },
        headers={
            "Authorization": f"Client-ID {os.environ['UNSPLASH_ACCESS_KEY']}",
            "Accept-Version": "v1",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def photo_to_record(photo: dict, festival_id: str) -> dict:
    user = photo.get("user", {})
    photographer = user.get("name", "Unknown")
    photographer_url = user.get("links", {}).get("html", "")
    photo_url = photo.get("links", {}).get("html", "")

    credit_html = (
        f'Photo by <a href="{photographer_url}?utm_source=soundcheck&utm_medium=referral">'
        f'{photographer}</a> on '
        f'<a href="{photo_url}?utm_source=soundcheck&utm_medium=referral">Unsplash</a>'
    )

    urls = photo.get("urls", {})
    return {
        "festival_id": festival_id,
        "unsplash_id": photo.get("id"),
        "url_regular": urls.get("regular"),
        "url_thumb": urls.get("thumb"),
        "url_full": urls.get("full"),
        "alt_text": photo.get("alt_description") or photo.get("description") or "",
        "photographer": photographer,
        "photographer_url": photographer_url,
        "credit_html": credit_html,
    }


def set_city_hero(supabase: Client, festival: dict) -> None:
    """
    Set festivals.hero_image_url to a city image — but only if one isn't
    already set, so manually-curated heroes are never overwritten.
    """
    if festival.get("hero_image_url"):
        return

    slug = festival["slug"]
    city = festival.get("city") or festival["name"]
    query = CITY_QUERIES.get(slug, DEFAULT_CITY_QUERY.format(city=city))

    photos = fetch_unsplash_photos(query, count=1)
    if not photos:
        console.log(f"[yellow]No city image found for {festival['name']} ({query})")
        return

    hero_url = photos[0].get("urls", {}).get("regular")
    if not hero_url:
        return

    try:
        supabase.table("festivals").update(
            {"hero_image_url": hero_url, "updated_at": "now()"}
        ).eq("id", festival["id"]).execute()
        console.log(f"[green]Set city hero for {festival['name']} ({query})")
    except Exception as e:
        log.error(f"Failed to set hero for {festival['slug']}: {e}")


def fetch_for_festival(supabase: Client, festival: dict) -> None:
    slug = festival["slug"]
    name = festival["name"]
    festival_id = festival["id"]

    # City hero image (only if not already set).
    set_city_hero(supabase, festival)

    query = FESTIVAL_QUERIES.get(slug, DEFAULT_QUERY.format(name=name))
    console.log(f"[cyan]Fetching Unsplash photos for {name} (query: {query})")

    photos = fetch_unsplash_photos(query, PHOTOS_PER_FESTIVAL)
    if not photos:
        console.log(f"[yellow]No photos found for {name}")
        return

    records = [photo_to_record(p, festival_id) for p in photos]

    for record in records:
        try:
            supabase.table("media").upsert(
                record, on_conflict="unsplash_id"
            ).execute()
        except Exception as e:
            log.error(f"Failed to upsert photo {record.get('unsplash_id')}: {e}")

    console.log(f"[green]Stored {len(records)} photos for {name}")


def main():
    parser = argparse.ArgumentParser(description="Fetch Unsplash media per festival")
    parser.add_argument("--festival", type=str, help="Festival slug")
    args = parser.parse_args()

    supabase = get_supabase()

    if args.festival:
        festival = supabase.table("festivals").select("*").eq("slug", args.festival).single().execute().data
        fetch_for_festival(supabase, festival)
        return

    festivals = supabase.table("festivals").select("*").eq("is_active", True).execute().data
    console.log(f"[cyan]Fetching media for {len(festivals)} festivals...")
    for festival in festivals:
        try:
            fetch_for_festival(supabase, festival)
        except Exception as e:
            log.error(f"Failed for {festival['slug']}: {e}")

    console.log("[green]Media fetch complete.")


if __name__ == "__main__":
    main()
