"""
recommend.py — v3.6 artist-similarity precompute
------------------------------------------------
Heuristic neighbours (PLAN: "heuristic first, vector later"). For each artist we
score every other artist by:
  • genre overlap   — Jaccard of genre sets
  • co-lineup graph — how many bills (festival+year) they share
  • popularity prior — a tiny tiebreak so the better-known match ranks first
and keep the top-K into artist_neighbors (read by lib/recommendations.ts).

Pure functions (jaccard / cooccurrence / compute_neighbors) carry the logic and
are covered by --self-test; the live path just loads artists+lineups and upserts.

Run:
    python recommend.py --self-test       # offline asserts, no DB/network
    python recommend.py                    # recompute all neighbours (live)
    python recommend.py --top-k 25
"""

from __future__ import annotations

import argparse
from collections import defaultdict

# ── Pure heuristic ─────────────────────────────────────────────
def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / len(a | b) if inter else 0.0


def bills_by_artist(lineups: list[dict]) -> dict[str, set]:
    """artist_id → set of (festival_id, year) bills it appeared on."""
    out: dict[str, set] = defaultdict(set)
    for ln in lineups:
        aid, fid, yr = ln.get("artist_id"), ln.get("festival_id"), ln.get("year")
        if aid and fid and yr is not None:
            out[aid].add((fid, yr))
    return out


def _reason(g: float, c: float) -> str:
    if g > 0 and c > 0:
        return "blend"
    return "genre" if g > 0 else "co-lineup"


def compute_neighbors(artists: list[dict], lineups: list[dict], top_k: int = 20,
                      w_genre: float = 0.6, w_colineup: float = 0.4) -> list[dict]:
    """Return artist_neighbors rows: {artist_id, neighbor_id, score, reason}.
    ponytail: O(n²) over artists — fine nightly at catalog scale (~10³ artists);
    swap to blocking/ANN if the catalog ever reaches 10⁴+."""
    bills = bills_by_artist(lineups)
    genres = {a["id"]: set(g.lower() for g in (a.get("genres") or [])) for a in artists}
    pop = {a["id"]: (a.get("spotify_popularity") or 0) for a in artists}

    rows: list[dict] = []
    for a in artists:
        aid = a["id"]
        ag, ab = genres[aid], bills.get(aid, set())
        scored = []
        for b in artists:
            bid = b["id"]
            if bid == aid:
                continue
            g = jaccard(ag, genres[bid])
            bb = bills.get(bid, set())
            shared = len(ab & bb)
            # Symmetric (Jaccard) denominator, NOT min(): min() gives a 1-bill
            # obscure artist c=1.0 against a 40-bill superstar they happened to
            # share one stage with, flooding neighbours with popularity skew.
            c = shared / len(ab | bb) if shared else 0.0
            if g == 0.0 and c == 0.0:
                continue
            score = w_genre * g + w_colineup * c + 0.001 * pop[bid] / 100.0
            scored.append((score, bid, _reason(g, c)))
        scored.sort(reverse=True)
        for score, bid, reason in scored[:top_k]:
            rows.append({"artist_id": aid, "neighbor_id": bid,
                         "score": round(score, 6), "reason": reason})
    return rows


# ── Live path ──────────────────────────────────────────────────
def _run_live(top_k: int) -> None:
    import os
    from dotenv import load_dotenv
    from supabase import create_client
    from rich.console import Console
    load_dotenv()
    console = Console()
    sb = create_client(os.environ["NEXT_PUBLIC_SUPABASE_URL"],
                       os.environ["SUPABASE_SERVICE_ROLE_KEY"])

    artists = sb.table("artists").select("id, genres, spotify_popularity").execute().data or []
    lineups = sb.table("lineups").select("artist_id, festival_id, year").execute().data or []
    console.log(f"[cyan]computing neighbours for {len(artists)} artists over {len(lineups)} lineup rows")
    rows = compute_neighbors(artists, lineups, top_k=top_k)
    # Upsert in batches (idempotent on the (artist_id, neighbor_id) pk).
    for i in range(0, len(rows), 500):
        sb.table("artist_neighbors").upsert(
            rows[i:i + 500], on_conflict="artist_id,neighbor_id").execute()
    console.log(f"[green]wrote {len(rows)} neighbour rows")


# ── Self-test ──────────────────────────────────────────────────
def _self_test() -> None:
    assert jaccard({"a", "b"}, {"b", "c"}) == 1 / 3
    assert jaccard(set(), {"a"}) == 0.0
    assert jaccard({"a"}, {"a"}) == 1.0

    artists = [
        {"id": "rock1", "genres": ["rock", "indie"], "spotify_popularity": 50},
        {"id": "rock2", "genres": ["rock", "indie"], "spotify_popularity": 80},  # genre twin
        {"id": "edm1", "genres": ["edm", "house"], "spotify_popularity": 60},
        {"id": "rock3", "genres": ["rock"], "spotify_popularity": 40},            # co-bill w/ rock1
    ]
    lineups = [
        {"artist_id": "rock1", "festival_id": "f1", "year": 2026},
        {"artist_id": "rock3", "festival_id": "f1", "year": 2026},  # shares a bill with rock1
        {"artist_id": "edm1", "festival_id": "f2", "year": 2026},
    ]
    rows = compute_neighbors(artists, lineups, top_k=5)

    # rock1's neighbours: rock2 (genre twin) + rock3 (genre+co-bill 'blend'); no edm1.
    n = {r["neighbor_id"]: r for r in rows if r["artist_id"] == "rock1"}
    assert "edm1" not in n, n
    assert "rock2" in n and "rock3" in n, n
    assert n["rock3"]["reason"] == "blend", n["rock3"]  # shared genre AND bill
    # rock3 shares a full bill with rock1 (co-lineup norm = 1) AND genre → outranks rock2.
    assert n["rock3"]["score"] >= n["rock2"]["score"], n

    # Symmetric-ish: edm1 has no genre/bill overlap → no neighbours.
    assert not any(r["artist_id"] == "edm1" for r in rows), "edm1 should have no neighbours"
    print("recommend: all checks passed")


def main() -> None:
    p = argparse.ArgumentParser(description="v3.6 artist-similarity precompute")
    p.add_argument("--self-test", action="store_true", help="offline asserts, no DB")
    p.add_argument("--top-k", type=int, default=20, help="neighbours kept per artist")
    args = p.parse_args()
    if args.self_test:
        _self_test()
        return
    _run_live(args.top_k)


if __name__ == "__main__":
    main()
