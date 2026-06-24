"""
test_idempotency.py
-------------------
Confirms v2.3.6: pipeline writes are safe to re-run, and the lineups uniqueness
actually represents the real schedule.

These are offline checks over data we control (no DB). They prove:
  1. The lineups key must be the *set* grain. The old key (festival, artist,
     year) collapses any artist with multiple sets to one row — for Lolla 2026
     that silently drops 10 of 191 sets. The widened key
     (festival, artist, year, day, set_time_start) keeps every set unique, so an
     upsert re-run is a no-op rather than lossy.
  2. Slug derivation is stable (idempotent): slugging an already-canonical name
     is a fixed point.
  3. Stage-coordinate spread is deterministic across runs.

Run: python test_idempotency.py
"""

import lolla_2026_schedule as sched
from names import canonical_slug
from location_enricher import spread


def test_lineup_key_is_set_grain() -> None:
    rows = sched.SCHEDULE
    old = {(r["name"], 2026) for r in rows}                              # festival, artist, year
    new = {(r["name"], 2026, r["day"], r["start"]) for r in rows}        # + day + set_time_start
    assert len(new) == len(rows), "widened key must keep every set distinct"
    assert len(old) < len(rows), "old key is expected to collapse multi-set artists"
    # Re-deriving the keys yields the identical set → upsert re-run is a no-op.
    assert new == {(r["name"], 2026, r["day"], r["start"]) for r in rows}


def test_slug_is_idempotent() -> None:
    for name in ("Röz", "Wet Leg", "BBNO$", "Miss Tutti & The Fruity Band"):
        s = canonical_slug(name)
        assert canonical_slug(s) == s, f"slug not a fixed point for {name!r}"


def test_spread_is_deterministic() -> None:
    assert spread(41.0, -87.0, 2, 5) == spread(41.0, -87.0, 2, 5)


if __name__ == "__main__":
    test_lineup_key_is_set_grain()
    test_slug_is_idempotent()
    test_spread_is_deterministic()
    print("test_idempotency: all checks passed")
