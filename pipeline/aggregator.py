"""
aggregator.py — v3.2 multi-festival metadata aggregator
-------------------------------------------------------
One AggregatorAdapter (subclasses the v3.0 SourceAdapter) that fills the festival
*metadata spine* — name, venue, city/state, coords, date range — for many festivals
from free event APIs. The exact fields the v3.1 gate checks, one adapter for all of
them. It writes festival rows ONLY (no lineups: provider lineup depth is too shallow
to trust); lineup/schedule depth stays curated / scraper-driven (see lineup_adapter.py).

Two providers behind a small strategy so a third slots in later:
  - Ticketmaster Discovery (primary; same API key lineup_scraper.py already uses)
  - SeatGeek (optional cross-validation; degrades to no-op without SEATGEEK_CLIENT_ID)

normalize() cross-merges the providers per target: agreement wins, gaps get filled,
date conflicts prefer Ticketmaster and are counted into the run-log stats. The merge
into the DB is coalesce-forward / trust-ordered — see ingest.merge_festival_fields.

Driven per-festival by ingest_festivals.py (one ingestion_runs row per festival, so
v3.1 freshness tracks each festival independently). Offline self-test: test_aggregator.py.
"""

from __future__ import annotations

import os
import csv
import hashlib
import logging
import datetime as dt
from dataclasses import dataclass

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

import ingest  # SourceAdapter, Normalized, register

log = logging.getLogger(__name__)

_TARGETS_CSV = os.path.join(os.path.dirname(__file__), "festival_targets.csv")


# ── Target list (curated; data, not code) ──────────────────────
@dataclass
class Target:
    slug: str
    name: str
    city: str = ""
    state: str = ""
    tier: str = "standard"        # 'flagship' | 'standard'
    tm_keyword: str = ""
    seatgeek_query: str = ""

    def __post_init__(self):
        # Fall back to the display name when a provider query column is blank.
        self.tm_keyword = self.tm_keyword or self.name
        self.seatgeek_query = self.seatgeek_query or self.name


def load_targets(path: str = _TARGETS_CSV) -> list[Target]:
    """Parse festival_targets.csv → [Target]. Blank lines / '#'-comments skipped."""
    out: list[Target] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            slug = (row.get("slug") or "").strip()
            if not slug or slug.startswith("#"):
                continue
            out.append(Target(
                slug=slug,
                name=(row.get("name") or "").strip(),
                city=(row.get("city") or "").strip(),
                state=(row.get("state") or "").strip(),
                tier=(row.get("tier") or "standard").strip(),
                tm_keyword=(row.get("tm_keyword") or "").strip(),
                seatgeek_query=(row.get("seatgeek_query") or "").strip(),
            ))
    return out


# ── Helpers ────────────────────────────────────────────────────
def _f(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _parse_iso(ts: str) -> dt.datetime:
    ts = ts.replace("Z", "+00:00")
    d = dt.datetime.fromisoformat(ts)
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def _is_main_festival_event(event_name: str, keyword: str) -> bool:
    """True if a TM event IS the festival, not an aftershow/side event.
    (Same heuristic as lineup_scraper, kept local to avoid coupling.)"""
    name, kw = event_name.lower().strip(), keyword.lower().strip()
    if name == kw:
        return True
    if any(m in name for m in
           ("aftershow", "after show", "after-show", "official", "feat", "present", "sold out")):
        return False
    return name.startswith(kw)


def _edition_range(dates: list[str]) -> tuple[str | None, str | None]:
    """Given festival-day dates across possibly several years, return the
    (min, max) of the SOONEST edition — group by year, take the smallest year."""
    valid = sorted(d for d in dates if d and len(d) >= 4)
    if not valid:
        return None, None
    soonest_year = min(d[:4] for d in valid)
    edition = [d for d in valid if d[:4] == soonest_year]
    return edition[0], edition[-1]


# ── Providers ──────────────────────────────────────────────────
# Each returns a candidate dict or None:
#   {provider, name, venue, city, state, latitude, longitude, start_date, end_date}
def normalize_tm(data: dict, target: Target) -> dict | None:
    """Pure: map a Ticketmaster events.json payload → a candidate. Testable offline."""
    events = (data.get("_embedded") or {}).get("events") or []
    main = [e for e in events if _is_main_festival_event(e.get("name", ""), target.tm_keyword)]
    if not main:
        return None
    dates = [((e.get("dates") or {}).get("start") or {}).get("localDate") for e in main]
    start, end = _edition_range([d for d in dates if d])
    venues = (main[0].get("_embedded") or {}).get("venues") or [{}]
    v = venues[0]
    loc = v.get("location") or {}
    return {
        "provider": "ticketmaster",
        "name": target.name,
        "venue": v.get("name"),
        "city": (v.get("city") or {}).get("name"),
        "state": (v.get("state") or {}).get("stateCode"),
        "latitude": _f(loc.get("latitude")),
        "longitude": _f(loc.get("longitude")),
        "start_date": start,
        "end_date": end,
    }


def normalize_seatgeek(data: dict, target: Target) -> dict | None:
    """Pure: map a SeatGeek /events payload → a candidate. Testable offline."""
    events = data.get("events") or []
    if not events:
        return None
    dates = [(e.get("datetime_local") or "")[:10] for e in events]
    start, end = _edition_range([d for d in dates if d])
    v = events[0].get("venue") or {}
    loc = v.get("location") or {}
    return {
        "provider": "seatgeek",
        "name": target.name,
        "venue": v.get("name"),
        "city": v.get("city"),
        "state": v.get("state"),
        "latitude": _f(loc.get("lat")),
        "longitude": _f(loc.get("lon")),
        "start_date": start,
        "end_date": end,
    }


class TicketmasterProvider:
    name = "ticketmaster"

    def __init__(self):
        self.key = os.environ["TICKETMASTER_API_KEY"]  # already used by lineup_scraper

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def _get(self, params: dict) -> dict:
        params = {**params, "apikey": self.key}
        r = requests.get("https://app.ticketmaster.com/discovery/v2/events.json",
                         params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    def search(self, target: Target) -> dict | None:
        data = self._get({"keyword": target.tm_keyword, "classificationName": "Music",
                          "countryCode": "US", "size": 30, "sort": "date,asc"})
        return normalize_tm(data, target)


class SeatGeekProvider:
    name = "seatgeek"

    def __init__(self):
        self.client_id = os.environ["SEATGEEK_CLIENT_ID"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def _get(self, params: dict) -> dict:
        params = {**params, "client_id": self.client_id}
        r = requests.get("https://api.seatgeek.com/2/events", params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    def search(self, target: Target) -> dict | None:
        data = self._get({"q": target.seatgeek_query, "type": "music_festival",
                          "per_page": 25, "sort": "datetime_local.asc"})
        return normalize_seatgeek(data, target)


def build_providers(names: list[str]) -> list:
    """Instantiate enabled providers; skip (warn) any whose key is absent."""
    out = []
    for n in names:
        try:
            if n == "ticketmaster":
                out.append(TicketmasterProvider())
            elif n == "seatgeek":
                out.append(SeatGeekProvider())
            else:
                log.warning("unknown provider %r — skipped", n)
        except KeyError as e:
            log.warning("provider %r disabled: missing env %s", n, e)
    return out


# ── Cross-source merge ─────────────────────────────────────────
_MERGE_FIELDS = ("venue", "city", "state", "latitude", "longitude", "start_date", "end_date")


def _coords_disagree(a, b) -> bool:
    return a is not None and b is not None and abs(a - b) > 0.05  # ~5km


def merge_candidates(candidates: list[dict], target: Target) -> tuple[dict | None, dict]:
    """Combine provider candidates (priority = list order, TM first) into one festival
    dict. First non-null wins per field; conflicts are counted into stats. Returns
    (festival_dict | None, stats). None when nothing usable (no dates and no coords)."""
    cands = [c for c in candidates if c]
    stats = {"providers": [c["provider"] for c in cands], "date_conflicts": 0, "coord_conflicts": 0}
    if not cands:
        return None, stats

    fest: dict = {"slug": target.slug, "name": target.name}
    for fld in _MERGE_FIELDS:
        for c in cands:
            if c.get(fld) is not None:
                fest[fld] = c[fld]
                break

    # Count cross-provider disagreement on the high-value fields (TM value is kept).
    starts = [c.get("start_date") for c in cands if c.get("start_date")]
    if len(set(starts)) > 1:
        stats["date_conflicts"] = 1
    lats = [c.get("latitude") for c in cands if c.get("latitude") is not None]
    if len(lats) > 1 and _coords_disagree(lats[0], lats[1]):
        stats["coord_conflicts"] = 1
    stats["agreement"] = len(cands) > 1 and not stats["date_conflicts"] and not stats["coord_conflicts"]

    usable = fest.get("start_date") or fest.get("latitude") is not None or fest.get("venue")
    return (fest if usable else None), stats


# ── Staleness rotation (pure) ──────────────────────────────────
def select_stale_targets(target_slugs: list[str], latest_success: dict[str, str],
                         now: dt.datetime, batch_size: int) -> list[str]:
    """Pick up to batch_size targets to refresh: never-ingested first (they have no
    freshness contract yet), then oldest successful run first. Stable within a tier,
    so CSV order breaks ties deterministically."""
    def key(slug: str):
        ts = latest_success.get(slug)
        return (1, _parse_iso(ts)) if ts else (0, now)  # 0 < 1 → never-ingested first
    return sorted(target_slugs, key=key)[:batch_size]


def shard_targets(slugs: list[str], shard: int, shards: int) -> list[str]:
    """Partition slugs across `shards` parallel cron runners by a STABLE hash (not
    Python's salted hash, which varies per process). The partitions are complete and
    disjoint, so the matrix covers every target exactly once."""
    if shards <= 1:
        return list(slugs)
    return [s for s in slugs
            if int(hashlib.md5(s.encode()).hexdigest(), 16) % shards == shard]


# ── Adapter ────────────────────────────────────────────────────
@ingest.register
class AggregatorAdapter(ingest.SourceAdapter):
    key = "aggregator"
    trust = "aggregator"
    festival_merge = "coalesce"   # tells run() to merge, not clobber, festival rows

    def fetch(self):
        target = self.config["target"]
        if isinstance(target, dict):
            target = Target(**target)
        providers = build_providers(self.config.get("providers", ["ticketmaster"]))
        candidates = []
        for p in providers:
            try:
                c = p.search(target)
            except Exception as e:  # noqa: BLE001 — one provider down ≠ run failure
                log.warning("provider %s failed for %s: %s", p.name, target.slug, e)
                c = None
            if c:
                candidates.append(c)
        return {"target": target, "candidates": candidates}

    def normalize(self, raw) -> ingest.Normalized:
        fest, stats = merge_candidates(raw["candidates"], raw["target"])
        self.stats = stats   # surfaced into the ingestion_runs row by run()
        return ingest.Normalized(festivals=[fest] if fest else [])
