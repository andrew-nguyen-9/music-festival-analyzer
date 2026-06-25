"""
ingest_festivals.py — v3.2 festival-metadata runner
---------------------------------------------------
Drives the AggregatorAdapter over the curated target list, ONE festival per run()
so each gets its own ingestion_runs row (v3.1 freshness is per-festival).

  python ingest_festivals.py --all              # one-time backfill (every target)
  python ingest_festivals.py --batch 30         # daily cron: the 30 stalest targets
  python ingest_festivals.py --festival coachella
  python ingest_festivals.py --batch 30 --dry-run   # show the rotation pick, no writes

The daily cron uses --batch so it never refreshes all ~200 at once: never-ingested
targets go first, then oldest-success first, so every festival cycles inside the 30-day
freshness window without blowing the cron time budget. See db/seed_sources.sql for the
`festival-aggregator` source row this reads (providers + which targets file).
"""

from __future__ import annotations

import argparse
import datetime as dt

from dotenv import load_dotenv
from rich.console import Console

import ingest
from aggregator import (  # noqa: F401 (import registers the adapter)
    AggregatorAdapter, load_targets, select_stale_targets, shard_targets,
)

load_dotenv()
console = Console()


def _latest_success(store, slugs: list[str]) -> dict[str, str]:
    """festival_slug → newest successful ingestion_run started_at, scoped to targets."""
    rows = (store.c.table("ingestion_runs")
            .select("festival_slug, started_at")
            .eq("status", "success").in_("festival_slug", slugs)
            .execute().data or [])
    latest: dict[str, str] = {}
    for r in rows:
        slug, ts = r.get("festival_slug"), r.get("started_at")
        if slug and (slug not in latest or ts > latest[slug]):
            latest[slug] = ts
    return latest


def main() -> None:
    p = argparse.ArgumentParser(description="v3.2 festival-metadata aggregator runner")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true", help="process every target (backfill)")
    g.add_argument("--batch", type=int, help="process the N stalest targets (daily cron)")
    g.add_argument("--festival", help="process one target by slug")
    p.add_argument("--dry-run", action="store_true", help="print the chosen targets, no writes")
    p.add_argument("--shard", type=int, default=0, help="this runner's shard index (matrix cron)")
    p.add_argument("--shards", type=int, default=1, help="total shards (stable hash partition)")
    args = p.parse_args()

    targets = load_targets()
    if args.shards > 1:  # keep only this runner's slice of the target list
        keep = set(shard_targets([t.slug for t in targets], args.shard, args.shards))
        targets = [t for t in targets if t.slug in keep]
    by_slug = {t.slug: t for t in targets}

    store = ingest.SupabaseStore(ingest.get_supabase())
    src = store.c.table("sources").select("id, config, trust").eq(
        "slug", "festival-aggregator").execute().data
    if not src:
        console.log("[red]No 'festival-aggregator' source row — apply db/seed_sources.sql first.")
        raise SystemExit(1)
    src = src[0]
    cfg = src.get("config") or {}

    if args.festival:
        chosen = [by_slug[args.festival]] if args.festival in by_slug else []
        if not chosen:
            console.log(f"[red]Unknown target slug: {args.festival}")
            raise SystemExit(1)
    elif args.all:
        chosen = targets
    else:  # --batch: staleness rotation
        latest = _latest_success(store, list(by_slug))
        slugs = select_stale_targets(list(by_slug), latest, dt.datetime.now(dt.timezone.utc), args.batch)
        chosen = [by_slug[s] for s in slugs]

    console.log(f"[cyan]Aggregator: {len(chosen)} target(s) "
                f"(providers={cfg.get('providers', ['ticketmaster'])})")
    if args.dry_run:
        for t in chosen:
            console.log(f"  • {t.slug} ({t.tier})")
        return

    for t in chosen:
        adapter = AggregatorAdapter({**cfg, "target": t})
        ingest.run(adapter, store, source_id=src["id"], festival_slug=t.slug,
                   trust=src.get("trust") or "aggregator")


if __name__ == "__main__":
    main()
