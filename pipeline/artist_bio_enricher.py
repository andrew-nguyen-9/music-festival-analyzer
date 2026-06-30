"""
artist_bio_enricher.py
----------------------
v4 artist enrichment for the data Spotify's 2026 API will NOT give us.

Root cause (diagnosed v4.1): for our client-credentials token the Spotify Web
API now returns `popularity`, `followers` and `genres` as null on BOTH /search
and /artists/{id} (verified: even Olivia Rodrigo → popularity null). spotify_sync
therefore can only land `spotify_id` + image. And Spotify has never exposed a
bio. So artist pages render the "still gathering data" EmptyState.

This script fills the gap from free, key-less sources:
  - Bio + genres ← MusicBrainz (artist → tags + Wikipedia/Wikidata relation),
    then the Wikipedia REST summary `extract` for the bio text.
  - Popularity + followers + image ← Deezer (fan count → 0-100 popularity proxy,
    same log-scale the legacy artist_enricher uses).

Writes resolve into the `artists` table columns (bio, genres, spotify_popularity,
spotify_followers, image_url) — which the frontend already reads as the fallback
under `withSpotifyCache` (`cache.X ?? artists.X`), so no frontend change is
needed. A row is also upserted into `artist_bio_cache` as a TTL freshness ledger
(best-effort: if that table isn't migrated yet, the write is skipped with a
warning and the run still succeeds).

Idempotent: by default only artists with no bio are processed; `--force` refetches
everyone. Re-runnable safely.

Run:
    python artist_bio_enricher.py --festival lollapalooza --year 2026
    python artist_bio_enricher.py --artist "Hozier"
    python artist_bio_enricher.py --force --limit 20
"""

from __future__ import annotations

import os
import re
import math
import logging
import argparse
import unicodedata
from datetime import datetime, timezone

import requests
import musicbrainzngs as mb
from dotenv import load_dotenv
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from rich.console import Console
from rich.progress import track

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
console = Console()
log = logging.getLogger(__name__)

UA = "Soundcheck/4.0 (https://an9.dev)"
mb.set_useragent("Soundcheck", "4.0", "https://an9.dev")  # MB requires a UA; lib throttles to 1 req/s
BIO_TTL_SECONDS = 2_592_000  # 30 days; bios change rarely
MB_MIN_SCORE = 90            # MusicBrainz ext:score floor when names don't match exactly


def get_supabase() -> Client:
    return create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


# ── Name matching (mirrors spotify_sync.normalize) ──────────────

def normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name or "")
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_only.lower()).strip()


# ── MusicBrainz: genres (tags) + Wikipedia/Wikidata relation ────

@retry(retry=retry_if_exception_type(mb.NetworkError),
       stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=False)
def _mb_search(name: str) -> list[dict]:
    return mb.search_artists(artist=name, limit=5).get("artist-list", [])


@retry(retry=retry_if_exception_type(mb.NetworkError),
       stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=False)
def _mb_get(mbid: str) -> dict:
    return mb.get_artist_by_id(mbid, includes=["url-rels", "tags"]).get("artist", {})


def mb_lookup(name: str) -> dict | None:
    """Best MusicBrainz match for a name. Guards against wrong-artist bios:
    accepts only an exact normalized-name match, or the top hit at ext:score ≥ 90."""
    try:
        results = _mb_search(name) or []
    except Exception as e:  # tenacity exhausted / unexpected
        log.warning("MB search failed for %r: %s", name, e)
        return None
    if not results:
        return None

    target = normalize(name)
    chosen = next((r for r in results if normalize(r.get("name", "")) == target), None)
    if chosen is None:
        top = results[0]
        if int(top.get("ext:score", 0)) >= MB_MIN_SCORE:
            chosen = top
    if chosen is None:
        return None

    try:
        info = _mb_get(chosen["id"]) or {}
    except Exception as e:
        log.warning("MB get failed for %r: %s", name, e)
        info = {}

    tags = sorted(info.get("tag-list", []), key=lambda t: -int(t.get("count", 0)))
    # Drop decade/year-ish tags ("2020s", "1990s") — they aren't genres.
    genres = [t["name"] for t in tags
              if not re.fullmatch(r"\d{4}s?", t["name"].strip())][:5]
    rels = info.get("url-relation-list", [])
    wiki = next((r["target"] for r in rels if r["type"] == "wikipedia"), None)
    wikidata = next((r["target"] for r in rels if r["type"] == "wikidata"), None)
    return {"mbid": chosen["id"], "genres": genres, "wikipedia": wiki, "wikidata": wikidata}


# ── Wikipedia bio ───────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=False)
def _wiki_summary(title: str, lang: str = "en") -> str | None:
    url = (f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
           f"{requests.utils.quote(title, safe='')}")
    r = requests.get(url, timeout=10, headers={"User-Agent": UA})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    data = r.json()
    if data.get("type") == "disambiguation":
        return None
    return data.get("extract") or None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=False)
def _wikidata_enwiki_title(qid: str) -> str | None:
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    r = requests.get(url, timeout=10, headers={"User-Agent": UA})
    r.raise_for_status()
    ent = r.json().get("entities", {}).get(qid, {})
    sl = ent.get("sitelinks", {}).get("enwiki")
    return sl["title"] if sl else None


# Words that mark a Wikipedia page as being about a music act — used to gate the
# direct-search fallback so generic names ("Jade", "Sunshine", "Worship") don't
# graft a stranger's (or a gemstone's) page onto an artist.
_MUSIC_TERMS = re.compile(
    r"\b(singer|songwriter|rapper|musician|band|duo|trio|dj|disc jockey|"
    r"record producer|producer|vocalist|drummer|guitarist|bassist|"
    r"recording artist|girl group|boy band|music|hip hop|rock|pop|"
    r"electronic|r&b|indie)\b", re.I)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=False)
def _wiki_search(name: str) -> list[dict]:
    url = "https://en.wikipedia.org/w/rest.php/v1/search/page"
    r = requests.get(url, params={"q": name, "limit": 3}, timeout=10,
                     headers={"User-Agent": UA})
    r.raise_for_status()
    return r.json().get("pages", [])


def _wiki_search_bio(name: str) -> tuple[str | None, str | None]:
    """Direct Wikipedia search fallback when MusicBrainz has no wiki relation.
    Accepts a page only when its base title matches the artist name AND the page
    looks like a music act (description/excerpt carries a music term)."""
    try:
        pages = _wiki_search(name) or []
    except Exception:
        return None, None
    target = normalize(name)
    for pg in pages:
        title = pg.get("title", "")
        base = re.sub(r"\s*\(.*?\)\s*$", "", title)  # drop "(musician)" qualifier
        if normalize(base) != target:
            continue
        blob = f"{pg.get('description', '')} {pg.get('excerpt', '')}"
        if not _MUSIC_TERMS.search(blob):
            continue
        bio = _wiki_summary(title)
        if bio:
            return bio, f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
    return None, None


def resolve_bio(mb_info: dict | None, name: str) -> tuple[str | None, str | None, str | None]:
    """(bio, source, source_url). Tries MusicBrainz's Wikipedia/Wikidata relation
    first (most precise), then a guarded direct Wikipedia search."""
    mb_info = mb_info or {}
    wiki = mb_info.get("wikipedia")
    if wiki:
        # ".../wiki/Olivia%20Rodrigo" → "Olivia Rodrigo"
        title = requests.utils.unquote(wiki.rstrip("/").split("/wiki/")[-1])
        bio = _wiki_summary(title)
        if bio:
            return bio, "wikipedia", wiki
    wikidata = mb_info.get("wikidata")
    if wikidata:
        qid = wikidata.rstrip("/").split("/")[-1]
        title = _wikidata_enwiki_title(qid)
        if title:
            bio = _wiki_summary(title)
            if bio:
                return bio, "wikipedia", f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
    bio, url = _wiki_search_bio(name)
    if bio:
        return bio, "wikipedia", url
    return None, None, None


# ── Deezer: popularity proxy + followers + image ────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=False)
def deezer_stats(name: str) -> dict | None:
    r = requests.get("https://api.deezer.com/search/artist",
                     params={"q": name, "limit": 1}, timeout=10, headers={"User-Agent": UA})
    r.raise_for_status()
    items = r.json().get("data", [])
    if not items:
        return None
    it = items[0]
    # Require a sane name match so we don't graft a stranger's fan count on.
    if normalize(it.get("name", "")) != normalize(name):
        return None
    nb_fan = it.get("nb_fan", 0) or 0
    # log-scale fan count → 0-100 (10M fans ≈ 100); same proxy as legacy enricher.
    popularity = min(100, int(math.log10(max(1, nb_fan)) / math.log10(10_000_000) * 100))
    pic = it.get("picture_xl") or it.get("picture_big")
    if pic and "/artist//" in pic:  # Deezer placeholder for no image
        pic = None
    return {"spotify_popularity": popularity, "spotify_followers": nb_fan, "image_url": pic}


# ── Cache ledger (best-effort) ──────────────────────────────────

def upsert_bio_cache(sb: Client, artist_id: str, bio: str | None, source: str | None,
                     source_url: str | None, mbid: str | None, genres: list[str]) -> None:
    row = {
        "artist_id": artist_id,
        "bio": bio,
        "source": source or "none",
        "source_url": source_url,
        "mbid": mbid,
        "genres": genres or [],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "ttl_seconds": BIO_TTL_SECONDS,
    }
    try:
        sb.table("artist_bio_cache").upsert(row, on_conflict="artist_id").execute()
    except Exception as e:
        # Table not migrated yet → ledger is optional; the artists-table write is
        # the source of truth the frontend reads. Warn once, keep going.
        if not getattr(upsert_bio_cache, "_warned", False):
            console.log(f"[yellow]artist_bio_cache unavailable ({str(e)[:60]}…) — "
                        f"skipping TTL ledger, writing artists table only.")
            upsert_bio_cache._warned = True  # type: ignore[attr-defined]


# ── Selection ───────────────────────────────────────────────────

def select_artists(sb: Client, festival: str | None, year: int | None,
                   force: bool, limit: int | None) -> list[dict]:
    if festival:
        fest = sb.table("festivals").select("id").eq("slug", festival).single().execute()
        q = sb.table("lineups").select("artist_id, artists(id, name, bio)").eq(
            "festival_id", fest.data["id"])
        if year:
            q = q.eq("year", year)
        rows = q.execute().data
        seen, artists = set(), []
        for r in rows:
            a = r.get("artists")
            if a and a["id"] not in seen:
                seen.add(a["id"])
                artists.append(a)
    else:
        artists = sb.table("artists").select("id, name, bio").execute().data

    if not force:
        artists = [a for a in artists if not (a.get("bio") or "").strip()]
    return artists[:limit] if limit else artists


# ── Orchestration ───────────────────────────────────────────────

def enrich_one(sb: Client, artist: dict) -> str:
    name = artist["name"]
    mb_info = mb_lookup(name)
    bio = source = source_url = mbid = None
    genres: list[str] = []
    if mb_info:
        mbid = mb_info["mbid"]
        genres = mb_info["genres"]
    bio, source, source_url = resolve_bio(mb_info, name)

    deezer = deezer_stats(name) or {}

    updates: dict = {"updated_at": "now()"}
    if bio:
        updates["bio"] = bio
    if genres:
        updates["genres"] = genres
    if deezer.get("spotify_popularity") is not None:
        updates["spotify_popularity"] = deezer["spotify_popularity"]
        updates["spotify_followers"] = deezer["spotify_followers"]
    if deezer.get("image_url") and not artist.get("image_url"):
        updates["image_url"] = deezer["image_url"]

    if len(updates) > 1:  # more than just updated_at
        sb.table("artists").update(updates).eq("id", artist["id"]).execute()
    upsert_bio_cache(sb, artist["id"], bio, source, source_url, mbid, genres)

    if bio and genres:
        return "full"
    if bio or genres or "spotify_popularity" in updates:
        return "partial"
    return "miss"


def self_test() -> None:
    """Offline asserts for the matching/guard logic (no network). CI gate."""
    assert normalize("Tyler, The Creator") == "tyler the creator"
    assert normalize("Adéla") == "adela"
    # parenthetical qualifier stripped before the name-match check
    strip = lambda t: re.sub(r"\s*\(.*?\)\s*$", "", t)
    assert strip("Sombr (musician)") == "Sombr"
    assert strip("Jade") == "Jade"
    # music-term gate: accept a music descriptor, reject an unrelated one
    assert _MUSIC_TERMS.search("American singer and songwriter")
    assert _MUSIC_TERMS.search("English indie rock band")
    assert not _MUSIC_TERMS.search("a green gemstone used in jewellery")
    assert not _MUSIC_TERMS.search("a river in northeastern Spain")
    print("artist_bio_enricher self-test: all checks passed")


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    p = argparse.ArgumentParser(description="Enrich artist bios/genres/stats from MusicBrainz/Wikipedia/Deezer")
    p.add_argument("--self-test", action="store_true", help="Run offline logic checks and exit")
    p.add_argument("--festival", type=str)
    p.add_argument("--year", type=int)
    p.add_argument("--artist", type=str, help="Single artist by exact name")
    p.add_argument("--force", action="store_true", help="Refetch even if bio already present")
    p.add_argument("--limit", type=int)
    args = p.parse_args()

    if args.self_test:
        self_test()
        return

    sb = get_supabase()

    if args.artist:
        row = sb.table("artists").select("id, name, bio, image_url").ilike(
            "name", args.artist).limit(1).execute().data
        if not row:
            console.log(f"[red]Artist not found: {args.artist}")
            return
        console.log(f"[cyan]{enrich_one(sb, row[0])}: {row[0]['name']}")
        return

    artists = select_artists(sb, args.festival, args.year, args.force, args.limit)
    if not artists:
        console.log("[green]Nothing to enrich (all have bios). Use --force to refetch.")
        return

    console.log(f"[cyan]Enriching {len(artists)} artists from MusicBrainz/Wikipedia/Deezer…")
    stats = {"full": 0, "partial": 0, "miss": 0}
    for a in track(artists, description="Enriching…"):
        try:
            stats[enrich_one(sb, a)] += 1
        except Exception as e:  # one artist must not sink the run
            log.error("enrich failed for %s: %s", a["name"], e)
            stats["miss"] += 1

    console.log(f"[green]Done. full={stats['full']} partial={stats['partial']} miss={stats['miss']} "
                f"/ {len(artists)} artists.")


if __name__ == "__main__":
    main()
