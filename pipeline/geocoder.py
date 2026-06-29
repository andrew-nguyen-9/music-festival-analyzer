"""
geocoder.py
-----------
Thin Nominatim (OpenStreetMap) geocoder for festival venues. Keyless — nothing
to add to secrets.

Usage policy (https://operations.osmfoundation.org/policies/nominatim/):
  - descriptive User-Agent with contact  -> USER_AGENT below
  - <= 1 request/second                  -> module throttle (_throttle)
  - cache results                        -> callers persist lat/lng in the DB
                                            (festivals.latitude/longitude +
                                            geocoded_at), so the daily cron never
                                            re-hits the API.

Nominatim resolves venues/cities ("Grant Park, Chicago") but NOT festival stages
inside a park — per-stage coordinates are seeded from known layout data
(location_enricher.LOLLA_STAGES), not from here.

Self-test (no network): python geocoder.py
"""

from __future__ import annotations

import time
import logging

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "soundcheck/2.3 (andrewng9999@gmail.com)"
MIN_INTERVAL = 1.1  # seconds between requests (policy: <= 1 req/s, + margin)

_last_call = 0.0


def _throttle() -> None:
    """Block until >= MIN_INTERVAL has elapsed since the last request."""
    global _last_call
    wait = MIN_INTERVAL - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def _parse(results: list) -> tuple[float, float] | None:
    """Pure: first usable (lat, lon) from a Nominatim JSON array, or None."""
    for r in results or []:
        try:
            return float(r["lat"]), float(r["lon"])
        except (KeyError, TypeError, ValueError):
            continue
    return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def _request(query: str) -> list:
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": query, "format": "json", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def geocode(query: str) -> tuple[float, float] | None:
    """Geocode a venue/place string to (lat, lon). Throttled + retried. Returns
    None when Nominatim has no hit (the caller decides any fallback)."""
    if not query or not query.strip():
        return None
    _throttle()
    try:
        return _parse(_request(query))
    except Exception as e:  # network/HTTP after retries — degrade, don't crash the run
        log.warning(f"geocode failed for {query!r}: {e}")
        return None


def _demo() -> None:
    assert _parse([{"lat": "41.8758", "lon": "-87.6189"}]) == (41.8758, -87.6189)
    assert _parse([]) is None
    assert _parse(None) is None
    # Skips an unparseable first hit, takes the next usable one.
    assert _parse([{"lat": "bad"}, {"lat": "1.0", "lon": "2.0"}]) == (1.0, 2.0)
    print("geocoder: all checks passed")


if __name__ == "__main__":
    _demo()
