"""
artist_enricher.py
------------------
Pulls artist metadata from Spotify for all artists in the artists
table, and updates their records in Supabase.

Run:
    python artist_enricher.py                    # enrich all artists missing Spotify data
    python artist_enricher.py --artist "Hozier"  # enrich a single artist
    python artist_enricher.py --festival "lollapalooza" --year 2026

Schedule: Daily via GitHub Actions (etl_daily.yml)
"""

import os
import time
import logging
import argparse
from dotenv import load_dotenv

import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.console import Console
from rich.progress import track

load_dotenv()
console = Console()
log = logging.getLogger(__name__)


def get_supabase() -> Client:
    return create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )


def get_spotify() -> spotipy.Spotify:
    auth = SpotifyClientCredentials(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    )
    return spotipy.Spotify(auth_manager=auth)


import math

_SPOTIFY_UNAVAILABLE = False  # set True after first 403 to skip remaining Spotify calls


def _deezer_search(artist_name: str) -> dict | None:
    try:
        resp = requests.get(
            "https://api.deezer.com/search/artist",
            params={"q": artist_name, "limit": 1},
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json().get("data", [])
        if not items:
            return None
        item = items[0]
        pic = item.get("picture_xl") or item.get("picture_big")
        if pic and "/artist//" in pic:
            pic = None
        return {"id": item["id"], "name": item["name"], "picture": pic, "nb_fan": item.get("nb_fan", 0)}
    except Exception as e:
        log.warning(f"Deezer search failed for {artist_name}: {e}")
        return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def fetch_deezer_image(artist_name: str) -> str | None:
    result = _deezer_search(artist_name)
    return result["picture"] if result else None


def enrich_from_deezer(artist_name: str) -> dict | None:
    """
    Primary enrichment when Spotify is unavailable.
    Returns image_url + a popularity proxy derived from fan count (0-100).
    """
    result = _deezer_search(artist_name)
    if not result:
        return None
    nb_fan = result.get("nb_fan", 0)
    # Log-scale fan count → 0-100 popularity proxy (10M fans ≈ 100)
    popularity = min(100, int(math.log10(max(1, nb_fan)) / math.log10(10_000_000) * 100))
    return {
        "image_url": result.get("picture"),
        "spotify_popularity": popularity,
    }


def enrich_from_spotify(sp: spotipy.Spotify, artist_name: str) -> dict | None:
    """
    Searches Spotify for an artist by name. Returns None if Spotify is
    unavailable (403) so the caller can fall back to Deezer.
    """
    global _SPOTIFY_UNAVAILABLE
    if _SPOTIFY_UNAVAILABLE:
        return None
    try:
        results = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)
        items = results.get("artists", {}).get("items", [])
        if not items:
            return None

        a = items[0]
        top_tracks = sp.artist_top_tracks(a["id"], country="US").get("tracks", [])
        preview_url = next((t["preview_url"] for t in top_tracks if t.get("preview_url")), None)

        image_url = a["images"][0]["url"] if a.get("images") else fetch_deezer_image(artist_name)

        return {
            "spotify_id": a["id"],
            "spotify_url": a["external_urls"].get("spotify"),
            "spotify_followers": a["followers"]["total"],
            "spotify_popularity": a["popularity"],
            "genres": a.get("genres", []),
            "image_url": image_url,
            "preview_url": preview_url,
        }
    except Exception as e:
        msg = str(e)
        if "403" in msg and "premium" in msg.lower():
            _SPOTIFY_UNAVAILABLE = True
            log.warning("Spotify 403 — switching to Deezer for remaining artists")
        else:
            log.warning(f"Spotify lookup failed for {artist_name}: {e}")
        return None


def enrich_artists(supabase: Client, sp: spotipy.Spotify, artists: list[dict]) -> None:
    spotify_ok = 0
    deezer_ok = 0
    skipped = 0

    for artist in track(artists, description="Enriching artists..."):
        name = artist["name"]

        enrichment = enrich_from_spotify(sp, name)
        source = "spotify"

        if not enrichment:
            enrichment = enrich_from_deezer(name)
            source = "deezer"

        if not enrichment:
            console.log(f"[yellow]No data for: {name}")
            skipped += 1
            continue

        enrichment["updated_at"] = "now()"

        try:
            supabase.table("artists").update(enrichment).eq("id", artist["id"]).execute()
            pop = enrichment.get("spotify_popularity", "?")
            if source == "spotify":
                spotify_ok += 1
            else:
                deezer_ok += 1
                console.log(f"[dim]Deezer: {name} (pop~{pop})")
        except Exception as e:
            log.error(f"Failed to update {name}: {e}")
            skipped += 1

        time.sleep(0.05)

    console.log(f"[green]Enriched {spotify_ok} via Spotify, {deezer_ok} via Deezer, {skipped} skipped")


def get_artists_to_enrich(supabase: Client, festival_slug: str | None = None, year: int | None = None) -> list[dict]:
    """
    Returns artists missing Spotify data, optionally filtered by festival/year.
    """
    if festival_slug:
        # Get artists in a specific festival lineup
        festival = supabase.table("festivals").select("id").eq("slug", festival_slug).single().execute()
        festival_id = festival.data["id"]

        query = (
            supabase.table("lineups")
            .select("artist_id, artists(*)")
            .eq("festival_id", festival_id)
        )
        if year:
            query = query.eq("year", year)

        result = query.execute()
        return [row["artists"] for row in result.data if row.get("artists")]
    else:
        # All artists missing Spotify data
        result = supabase.table("artists").select("*").is_("spotify_id", "null").execute()
        return result.data


def upsert_artist(supabase: Client, sp: spotipy.Spotify, name: str) -> None:
    """Create or update a single artist record."""
    from slugify import slugify

    slug = slugify(name)
    existing = supabase.table("artists").select("id").eq("slug", slug).execute()

    if not existing.data:
        supabase.table("artists").insert({"slug": slug, "name": name}).execute()
        result = supabase.table("artists").select("*").eq("slug", slug).single().execute()
        artist = result.data
    else:
        artist = existing.data[0]

    enrichment = enrich_from_spotify(sp, name)
    if enrichment:
        supabase.table("artists").update(enrichment).eq("id", artist["id"]).execute()
        console.log(f"[green]Upserted + enriched: {name}")
    else:
        console.log(f"[yellow]Created artist with no Spotify data: {name}")


def main():
    parser = argparse.ArgumentParser(description="Enrich artists via Spotify")
    parser.add_argument("--artist", type=str, help="Enrich a single artist by name")
    parser.add_argument("--festival", type=str, help="Enrich all artists in this festival slug")
    parser.add_argument("--year", type=int, help="Filter by lineup year (use with --festival)")
    args = parser.parse_args()

    supabase = get_supabase()
    sp = get_spotify()

    if args.artist:
        upsert_artist(supabase, sp, args.artist)
        return

    artists = get_artists_to_enrich(supabase, festival_slug=args.festival, year=args.year)
    if not artists:
        console.log("[yellow]No artists to enrich.")
        return

    console.log(f"[cyan]Enriching {len(artists)} artists...")
    enrich_artists(supabase, sp, artists)
    console.log("[green]Artist enrichment complete.")


if __name__ == "__main__":
    main()
