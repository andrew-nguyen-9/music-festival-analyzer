"""
lineup_adapter.py — v3.2 flagship lineup depth on the v3.0 contract
-------------------------------------------------------------------
Proves the scrape/API *lineup* path subclasses SourceAdapter the same way the
config-driven manual adapter does. Where AggregatorAdapter fills festival metadata
for many festivals, this writes day-by-day LINEUPS for one flagship from Ticketmaster
Discovery — exactly what lineup_scraper.py does, now routed through run() so it gets
the ingestion_runs row, per-row provenance (source_id), and the v2.3.3 trust triggers
for free instead of re-implementing client+retry+upsert.

We port ONE source as proof; the other ~25 flagships in lineup_scraper.FESTIVAL_CONFIG
migrate the same way when needed (not in v3.2 scope).

Run via a sources row + the festival CLI, e.g.:
  python ingest.py --source coachella-lineup-tm     # once seeded in db/seed_sources.sql
Offline self-test: test_aggregator.py (normalize over a fixture, no network).
"""

from __future__ import annotations

import os
import logging

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

import ingest
from names import canonical_name, canonical_slug

log = logging.getLogger(__name__)


def _is_main_festival_event(event_name: str, keyword: str) -> bool:
    name, kw = event_name.lower().strip(), keyword.lower().strip()
    if name == kw:
        return True
    if any(m in name for m in
           ("aftershow", "after show", "after-show", "official", "feat", "present", "sold out")):
        return False
    return name.startswith(kw)


def normalize_tm_lineup(data: dict, festival_slug: str, tm_keyword: str, year: int,
                        headliners_per_day: int) -> list[dict]:
    """Pure: Ticketmaster events.json → lineup rows. One row per (day, artist);
    the first `headliners_per_day` billed acts each day flagged is_headliner.
    Testable offline with a fixture payload."""
    events = (data.get("_embedded") or {}).get("events") or []
    kw_stem = (tm_keyword.split()[0] if tm_keyword else "").lower()
    lineups: list[dict] = []
    for e in events:
        name = e.get("name", "")
        day = ((e.get("dates") or {}).get("start") or {}).get("localDate", "")
        if not day or not day.startswith(str(year)):
            continue
        if not _is_main_festival_event(name, tm_keyword):  # skip aftershows/side events
            continue
        attractions = (e.get("_embedded") or {}).get("attractions") or []
        # Drop a leading attraction that's the festival itself, not an artist.
        if attractions and kw_stem and kw_stem in attractions[0].get("name", "").lower():
            attractions = attractions[1:]
        if len(attractions) < 5:   # too few → not a real festival-day entry
            continue
        for i, att in enumerate(attractions):
            an = (att.get("name") or "").strip()
            if not an:
                continue
            lineups.append({
                "festival_slug": festival_slug,
                "artist_slug": canonical_slug(an),
                "artist_name": canonical_name(an),
                "year": year,
                "day": day,
                "is_headliner": i < headliners_per_day,
            })
    return lineups


@ingest.register
class TicketmasterLineupAdapter(ingest.SourceAdapter):
    key = "ticketmaster_lineup"
    trust = "ticketmaster"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def fetch(self):
        return requests.get(
            "https://app.ticketmaster.com/discovery/v2/events.json",
            params={"keyword": self.config["tm_keyword"], "classificationName": "Music",
                    "countryCode": "US", "size": 50, "sort": "date,asc",
                    "apikey": os.environ["TICKETMASTER_API_KEY"]},
            timeout=15,
        ).json()

    def normalize(self, raw) -> ingest.Normalized:
        lineups = normalize_tm_lineup(
            raw, self.config["festival_slug"], self.config["tm_keyword"],
            int(self.config.get("year", 2026)), int(self.config.get("headliners_per_day", 2)),
        )
        return ingest.Normalized(lineups=lineups)
