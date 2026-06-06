"""
artist_enricher.py
------------------
Pulls artist metadata from Spotify and Apple Music for all artists
in the artists table, and updates their records in Supabase.

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


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def enrich_from_spotify(sp: spotipy.Spotify, artist_name: str) -> dict | None:
    """
    Searches Spotify for an artist by name, returns enrichment payload.
    """
    results = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)
    items = results.get("artists", {}).get("items", [])
    if not items:
        return None

    a = items[0]
    top_tracks = sp.artist_top_tracks(a["id"], country="US").get("tracks", [])
    preview_url = next((t["preview_url"] for t in top_tracks if t.get("preview_url")), None)

    return {
        "spotify_id": a["id"],
        "spotify_url": a["external_urls"].get("spotify"),
        "spotify_followers": a["followers"]["total"],
        "spotify_popularity": a["popularity"],
        "genres": a.get("genres", []),
        "image_url": a["images"][0]["url"] if a.get("images") else None,
        "preview_url": preview_url,
    }


def build_apple_music_url(artist_name: str) -> str:
    """
    Constructs a best-effort Apple Music search URL for an artist.
    Full Apple Music API integration requires a MusicKit token (JWT).
    See docs/API_REFERENCE.md for full Apple Music setup.
    """
    query = artist_name.replace(" ", "+")
    return f"https://music.apple.com/us/search?term={query}"


def enrich_artists(supabase: Client, sp: spotipy.Spotify, artists: list[dict]) -> None:
    for artist in track(artists, description="Enriching artists via Spotify..."):
        name = artist["name"]
        enrichment = enrich_from_spotify(sp, name)

        if not enrichment:
            console.log(f"[yellow]No Spotify match for: {name}")
            continue

        enrichment["apple_music_url"] = build_apple_music_url(name)
        enrichment["updated_at"] = "now()"

        try:
            supabase.table("artists").update(enrichment).eq("id", artist["id"]).execute()
            console.log(f"[green]Enriched: {name} (pop: {enrichment['spotify_popularity']})")
        except Exception as e:
            log.error(f"Failed to update {name}: {e}")

        time.sleep(0.1)  # Spotify rate limit buffer


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
        enrichment["apple_music_url"] = build_apple_music_url(name)
        supabase.table("artists").update(enrichment).eq("id", artist["id"]).execute()
        console.log(f"[green]Upserted + enriched: {name}")
    else:
        console.log(f"[yellow]Created artist with no Spotify data: {name}")


def main():
    parser = argparse.ArgumentParser(description="Enrich artists via Spotify + Apple Music")
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
