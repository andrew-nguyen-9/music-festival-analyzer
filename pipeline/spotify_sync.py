"""
spotify_sync.py
---------------
v2.2 Spotify sync worker. Fetches artist metadata from the Spotify Web API
(client-credentials flow, server-side only) and writes it to the
`artist_spotify_cache` table. The frontend reads that cache — it never calls
Spotify itself.

Designed around the 2026 Spotify API reality:
  - No bulk metadata endpoints  → artists are fetched individually.
  - Legacy "artist top tracks" removed → preview_url / top_tracks stay null;
    the frontend's auth-free Spotify embed handles playback instead.
  - Global /search capped at 10 items/request → we page with offset to give
    lesser-known acts a fair shot at a match.
  - Development Mode tightened → client-credentials still serves public data.

Name matching: festival artist names are matched to Spotify artists with a
normalized fuzzy ratio (stdlib difflib). A match is only written when the best
candidate clears MATCH_THRESHOLD; otherwise a "miss" row is cached so we don't
re-search the same unmatched name every run (it retries after the TTL).

Run:
    python spotify_sync.py                          # sync all stale/missing artists
    python spotify_sync.py --festival lollapalooza  # only this festival's lineup
    python spotify_sync.py --festival lollapalooza --year 2026
    python spotify_sync.py --force                  # ignore TTL, refetch everyone
    python spotify_sync.py --limit 20               # cap work (smoke test)

Schedule: daily via GitHub Actions (etl_daily.yml), manual --festival trigger.
Idempotent: safe to re-run; upserts on artist_id.
"""

from __future__ import annotations

import os
import re
import time
import logging
import argparse
import unicodedata
import threading
from datetime import datetime, timezone
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.exceptions import SpotifyException
from tenacity import retry, stop_after_attempt, retry_if_exception
from rich.console import Console
from rich.progress import track

if TYPE_CHECKING:  # supabase imported lazily so pure logic stays testable w/o it
    from supabase import Client

load_dotenv()
console = Console()
log = logging.getLogger(__name__)

# ── Tuning knobs ────────────────────────────────────────────────
# ponytail: defaults chosen for 600-ish artists under the 2026 rate caps;
# bump BATCH_SIZE / drop THROTTLE only if a run is too slow and 429s stay rare.
BATCH_SIZE = 5            # concurrent in-flight searches ("throttled Promise.all")
THROTTLE_SECONDS = 0.2    # pause between batches to stay under the rate limit
SEARCH_PAGES = 3          # /search pages to scan (10 items each) per artist
MATCH_THRESHOLD = 0.85    # min normalized ratio to accept a name match
DEFAULT_TTL = 604800      # 7 days; mirrors the table default
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
# Open question (PLAN.md) resolved here: target ≥ 90% of artists matched at
# MATCH_THRESHOLD; unmatched names fall back to a cached miss row (no Spotify
# fields) so the page degrades gracefully and the worker doesn't re-hammer search.
TARGET_MATCH_RATE = 0.90


def get_supabase() -> "Client":
    from supabase import create_client
    return create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def get_spotify() -> spotipy.Spotify:
    auth = SpotifyClientCredentials(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    )
    # spotipy's own retries off — tenacity owns backoff so we can honor Retry-After.
    return spotipy.Spotify(auth_manager=auth, retries=0)


# ── Name matching ───────────────────────────────────────────────

def normalize(name: str) -> str:
    """Lowercase, strip diacritics + punctuation, collapse whitespace."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-z0-9]+", " ", ascii_only.lower())
    return cleaned.strip()


def match_score(query: str, candidate: str) -> float:
    """Normalized similarity in [0, 1]. Exact normalized equality → 1.0."""
    q, c = normalize(query), normalize(candidate)
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    return SequenceMatcher(None, q, c).ratio()


def best_match(items: list[dict], name: str) -> tuple[dict | None, float]:
    """Pick the best-scoring Spotify artist item for a name. Ties broken by
    popularity so the canonical (more popular) act wins over soundalikes."""
    def pop(it: dict) -> int:
        # 2026: popularity is often null — coerce so the tie-break can't TypeError.
        return it.get("popularity") or 0

    best, best_score = None, 0.0
    for item in items:
        score = match_score(name, item.get("name", ""))
        if score > best_score or (
            score == best_score and best is not None and pop(item) > pop(best)
        ):
            best, best_score = item, score
    return best, best_score


# ── Spotify fetch (rate-limit resilient) ────────────────────────

def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, SpotifyException) and exc.http_status in RETRYABLE_STATUS


def _wait_spotify(retry_state) -> float:
    """Honor Retry-After on 429; otherwise exponential backoff capped at 30s."""
    exc = retry_state.outcome.exception()
    if isinstance(exc, SpotifyException) and exc.http_status == 429:
        headers = getattr(exc, "headers", None) or {}
        try:
            return float(headers.get("Retry-After", 1))
        except (TypeError, ValueError):
            return 1.0
    return min(2.0 ** retry_state.attempt_number, 30.0)


# 6 attempts (vs CLAUDE.md's baseline "3 retries"): a rate-limit storm can burn
# several 429s before Retry-After clears, so we allow more retries here to meet
# the v2.2 "survives a rate-limit storm" exit criterion.
@retry(
    retry=retry_if_exception(_is_retryable),
    wait=_wait_spotify,
    stop=stop_after_attempt(6),
    reraise=True,
)
def search_page(sp, name: str, offset: int) -> list[dict]:
    """One page of artist search (≤10 items — the 2026 cap). Retries on 429/5xx."""
    res = sp.search(q=name, type="artist", limit=10, offset=offset)
    return res.get("artists", {}).get("items", [])


def search_artist(sp, name: str) -> tuple[dict | None, float]:
    """Search up to SEARCH_PAGES pages, return the best fuzzy match + its score."""
    candidates: list[dict] = []
    for page in range(SEARCH_PAGES):
        items = search_page(sp, name, offset=page * 10)
        if not items:
            break
        candidates.extend(items)
        # An exact normalized hit on page 1 is good enough; stop paging.
        if any(match_score(name, it.get("name", "")) >= 0.999 for it in items):
            break
    return best_match(candidates, name)


# ── Cache row construction ──────────────────────────────────────

def fetch_top_tracks(sp, spotify_id: str) -> tuple[list | None, str | None]:
    """(top_tracks, preview_url) for an artist. Returns (None, None) on failure
    so coalesce-forward in build_row keeps any prior cache instead of wiping it.
    top_tracks is trimmed to what the playlist + preview UI needs."""
    try:
        tracks = sp.artist_top_tracks(spotify_id, country="US").get("tracks", [])
    except Exception as e:  # endpoint hiccup / rate limit — keep prior cache
        log.warning("top-tracks fetch failed for %s: %s", spotify_id, e)
        return None, None
    top = [
        {"uri": t.get("uri"), "id": t.get("id"), "name": t.get("name")}
        for t in tracks[:10]
        if t.get("uri") or t.get("id")
    ]
    preview = next((t.get("preview_url") for t in tracks if t.get("preview_url")), None)
    return (top or None), preview


def build_row(artist_id: str, item: dict | None, prev: dict | None = None,
              top_tracks: list | None = None, preview_url: str | None = None) -> dict:
    """Shape a cache row from a Spotify search item (or a miss when item=None).

    Coalesce-forward: in 2026 Spotify returns popularity/followers/genres
    inconsistently (often null), so a fresh null must never clobber a known-good
    value — we fall back to `prev` (the existing cache row). This makes the cache
    monotonically best-known and keeps a flaky empty search from wiping a match.
    """
    prev = prev or {}

    def keep(key: str, new):
        return new if new not in (None, [], "") else prev.get(key)

    if item is None:
        sid = fol = pop = img = None
        gen: list = []
    else:
        sid = item["id"]
        fol = (item.get("followers") or {}).get("total")
        pop = item.get("popularity")
        gen = item.get("genres") or []
        img = item["images"][0]["url"] if item.get("images") else None

    return {
        "artist_id": artist_id,
        "fetched_at": datetime.now(timezone.utc).isoformat(),  # trigger sets expires_at
        "ttl_seconds": DEFAULT_TTL,
        "spotify_id": keep("spotify_id", sid),
        "followers": keep("followers", fol),
        "popularity": keep("popularity", pop),
        "genres": keep("genres", gen) or [],
        "image_url": keep("image_url", img),
        # Populated from /artists/{id}/top-tracks (fetched in work()); coalesce so a
        # transient empty fetch never wipes a known-good cache (v2.11 fix, bug_001).
        "preview_url": keep("preview_url", preview_url),
        "top_tracks": keep("top_tracks", top_tracks),
        "raw": item,
    }


# ── Selecting which artists need a sync ─────────────────────────

def artists_for_festival(sb: Client, slug: str, year: int | None) -> list[dict]:
    fest = sb.table("festivals").select("id").eq("slug", slug).single().execute()
    q = sb.table("lineups").select("artist_id, artists(id, name)").eq(
        "festival_id", fest.data["id"]
    )
    if year:
        q = q.eq("year", year)
    rows = q.execute().data
    seen, out = set(), []
    for r in rows:
        a = r.get("artists")
        if a and a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
    return out


def select_stale(sb: Client, festival: str | None, year: int | None,
                 force: bool, limit: int | None) -> list[dict]:
    """Artists whose cache is missing or expired (or everyone, if --force)."""
    if festival:
        artists = artists_for_festival(sb, festival, year)
    else:
        # ponytail: PostgREST caps responses at ~1000 rows; fine at the current
        # ~672 artists. Add .range() pagination here if the catalog exceeds 1000.
        artists = sb.table("artists").select("id, name").execute().data

    if not force:
        now_iso = datetime.now(timezone.utc).isoformat()
        fresh = sb.table("artist_spotify_cache").select("artist_id").gt(
            "expires_at", now_iso
        ).execute().data
        fresh_ids = {r["artist_id"] for r in fresh}
        artists = [a for a in artists if a["id"] not in fresh_ids]

    return artists[:limit] if limit else artists


# ── Orchestration ───────────────────────────────────────────────

def load_existing(sb: "Client", artist_ids: list[str]) -> dict:
    """Map artist_id → its current cache row (for coalesce-forward)."""
    existing: dict = {}
    cols = "artist_id, spotify_id, followers, popularity, genres, image_url, preview_url, top_tracks"
    for i in range(0, len(artist_ids), 200):
        rows = sb.table("artist_spotify_cache").select(cols).in_(
            "artist_id", artist_ids[i:i + 200]
        ).execute().data
        existing.update({r["artist_id"]: r for r in rows})
    return existing


def sync(sb: "Client", sp, artists: list[dict]) -> dict:
    """Fetch in throttled concurrent batches; upsert all rows; return stats."""
    rows: list[dict] = []
    matched = 0
    lock = threading.Lock()
    existing = load_existing(sb, [a["id"] for a in artists])

    def work(artist: dict) -> dict:
        prev = existing.get(artist["id"])
        item, score = search_artist(sp, artist["name"])
        if item is None or score < MATCH_THRESHOLD:
            if item is not None:
                log.info("low-confidence match for %r: best=%r (%.2f) — caching miss",
                         artist["name"], item.get("name"), score)
            return build_row(artist["id"], None, prev)
        top, preview = fetch_top_tracks(sp, item["id"])
        return build_row(artist["id"], item, prev, top_tracks=top, preview_url=preview)

    batches = [artists[i:i + BATCH_SIZE] for i in range(0, len(artists), BATCH_SIZE)]
    for batch in track(batches, description="Syncing Spotify…"):
        with ThreadPoolExecutor(max_workers=BATCH_SIZE) as pool:
            futures = {pool.submit(work, a): a for a in batch}
            for fut in as_completed(futures):
                a = futures[fut]
                try:
                    row = fut.result()
                    with lock:
                        rows.append(row)
                        if row["spotify_id"]:
                            matched += 1
                except Exception as e:  # one artist failing must not sink the run
                    log.error("sync failed for %s: %s", a["name"], e)
        time.sleep(THROTTLE_SECONDS)

    # Bulk upsert in chunks — idempotent on the unique artist_id.
    for i in range(0, len(rows), 100):
        sb.table("artist_spotify_cache").upsert(
            rows[i:i + 100], on_conflict="artist_id"
        ).execute()

    return {"processed": len(rows), "matched": matched, "total": len(artists)}


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    parser = argparse.ArgumentParser(description="Sync Spotify data into artist_spotify_cache")
    parser.add_argument("--festival", type=str, help="Festival slug to target")
    parser.add_argument("--year", type=int, help="Lineup year (use with --festival)")
    parser.add_argument("--force", action="store_true", help="Ignore TTL; refetch all")
    parser.add_argument("--limit", type=int, help="Cap number of artists (smoke test)")
    args = parser.parse_args()

    sb = get_supabase()
    artists = select_stale(sb, args.festival, args.year, args.force, args.limit)
    if not artists:
        console.log("[green]Cache is fresh — nothing to sync.")
        return

    console.log(f"[cyan]Syncing {len(artists)} artists "
                f"({'forced' if args.force else 'stale/missing'})…")
    sp = get_spotify()
    stats = sync(sb, sp, artists)

    rate = stats["matched"] / stats["total"] if stats["total"] else 0
    style = "green" if rate >= TARGET_MATCH_RATE else "yellow"
    console.log(f"[{style}]Matched {stats['matched']}/{stats['total']} "
                f"({rate:.0%}) — target {TARGET_MATCH_RATE:.0%}. "
                f"Wrote {stats['processed']} cache rows.")


if __name__ == "__main__":
    main()
