"""
notify.py — v3.8 lineup change-detection (scaffold)
---------------------------------------------------
The pure, tested core of notifications: diff a festival's lineup between two
ingestion snapshots and fan changes out to the users who favourited an affected
artist. The actual delivery (web push / email) is an operator-wired step — see
docs/planning/v3/v3.4-3.5-3.8-scaffold.md — so _run_live only assembles + logs
the events for now.

Run:
    python notify.py --self-test     # offline asserts, no DB/network
"""

from __future__ import annotations

import argparse
from collections import defaultdict


# ── Pure change detection ──────────────────────────────────────
def lineup_delta(prev: set, curr: set) -> dict:
    """Added/removed artist ids between two lineup snapshots (sets of artist_id)."""
    return {"added": sorted(curr - prev), "removed": sorted(prev - curr)}


def notify_events(delta: dict, favorites_by_user: dict[str, set]) -> list[dict]:
    """For each user, emit one event per favourited artist that was added/dropped.
    favorites_by_user: user_id -> set of favourited artist_ids.

    Invert favourites once (artist -> users) and look up each changed artist, so
    cost is O(total_favorites + changes) rather than O(changes × all_users) — the
    fan-out path must not scan every user per changed artist."""
    fans_of: dict[str, list[str]] = defaultdict(list)
    for user_id, favs in favorites_by_user.items():
        for artist_id in favs:
            fans_of[artist_id].append(user_id)

    events: list[dict] = []
    for kind in ("added", "removed"):
        for artist_id in delta.get(kind, []):
            for user_id in fans_of.get(artist_id, []):
                events.append({"user_id": user_id, "artist_id": artist_id, "change": kind})
    return events


# ── Live scaffold (delivery deferred) ──────────────────────────
def _run_live() -> None:  # pragma: no cover - wiring pending
    from rich.console import Console
    Console().log(
        "[yellow]notify: delivery not wired yet. lineup_delta/notify_events are the "
        "tested core; hook them to ingestion_runs diffs + web-push/email per the v3.4 "
        "scaffold doc.[/yellow]"
    )


def _self_test() -> None:
    prev = {"a", "b", "c"}
    curr = {"b", "c", "d"}            # +d, -a
    delta = lineup_delta(prev, curr)
    assert delta == {"added": ["d"], "removed": ["a"]}, delta

    favorites = {"u1": {"a", "z"}, "u2": {"d"}, "u3": {"x"}}
    events = notify_events(delta, favorites)
    # u1 favourited the dropped 'a'; u2 favourited the added 'd'; u3 unaffected.
    assert {"user_id": "u1", "artist_id": "a", "change": "removed"} in events
    assert {"user_id": "u2", "artist_id": "d", "change": "added"} in events
    assert all(e["user_id"] != "u3" for e in events), events
    assert len(events) == 2, events

    # No change → no events.
    assert notify_events(lineup_delta(prev, prev), favorites) == []
    print("notify: all checks passed")


def main() -> None:
    p = argparse.ArgumentParser(description="v3.8 lineup change-detection")
    p.add_argument("--self-test", action="store_true", help="offline asserts, no DB")
    args = p.parse_args()
    if args.self_test:
        _self_test()
        return
    _run_live()


if __name__ == "__main__":
    main()
