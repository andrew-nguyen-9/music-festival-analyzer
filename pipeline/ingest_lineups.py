"""
ingest_lineups.py — v3.2.7 flagship lineup-depth runner
-------------------------------------------------------
Drives every enabled `ticketmaster_lineup` source (the flagship rows seeded in
db/seed_sources.sql) through the v3.0 orchestrator, so each gets an ingestion_runs
row + per-row provenance and the v2.3.3 trust triggers referee it vs. curated posters.

  python ingest_lineups.py                          # all flagship lineup sources
  python ingest_lineups.py --festival coachella     # one, by festival slug
  python ingest_lineups.py --shard 0 --shards 4     # matrix cron slice
  python ingest_lineups.py --dry-run                # list what would run, no writes

Kept separate from ingest_festivals.py (which does metadata + rotation): lineups have
no freshness rotation — flagships are few, so the matrix shard alone bounds cron time.
"""

from __future__ import annotations

import argparse

from dotenv import load_dotenv
from rich.console import Console

import ingest
from lineup_adapter import TicketmasterLineupAdapter  # noqa: F401 (registers adapter)
from aggregator import shard_targets

load_dotenv()
console = Console()


def main() -> None:
    p = argparse.ArgumentParser(description="v3.2.7 flagship lineup runner")
    p.add_argument("--festival", help="run only the source for this festival slug")
    p.add_argument("--dry-run", action="store_true", help="list sources, no writes")
    p.add_argument("--shard", type=int, default=0, help="this runner's shard index")
    p.add_argument("--shards", type=int, default=1, help="total shards (stable hash partition)")
    args = p.parse_args()

    store = ingest.SupabaseStore(ingest.get_supabase())
    rows = (store.c.table("sources").select("*")
            .eq("enabled", True).eq("adapter_key", "ticketmaster_lineup")
            .execute().data or [])

    if args.festival:
        rows = [r for r in rows if (r.get("config") or {}).get("festival_slug") == args.festival]
    if args.shards > 1:
        keep = set(shard_targets([r["slug"] for r in rows], args.shard, args.shards))
        rows = [r for r in rows if r["slug"] in keep]

    if not rows:
        console.log("[yellow]No matching ticketmaster_lineup sources.")
        return

    console.log(f"[cyan]Flagship lineups: {len(rows)} source(s)")
    if args.dry_run:
        for r in rows:
            console.log(f"  • {r['slug']} → {(r.get('config') or {}).get('festival_slug')}")
        return

    for r in rows:
        adapter = ingest.get_adapter(r["adapter_key"], r.get("config"))
        fest_slug = (r.get("config") or {}).get("festival_slug")
        console.log(f"[cyan]{r['slug']}")
        ingest.run(adapter, store, source_id=r["id"], festival_slug=fest_slug,
                   trust=r.get("trust") or "ticketmaster")


if __name__ == "__main__":
    main()
