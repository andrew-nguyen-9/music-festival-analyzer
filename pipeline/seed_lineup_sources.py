"""
seed_lineup_sources.py — v4.2
-----------------------------
Seeds `ticketmaster_lineup` source rows (the v3.0 source registry) for the top US
festivals from festival_targets.csv, so ingest_lineups.py actually has sources to
run. db/seed_sources.sql was never applied to the live DB (only 3 manual_config
rows exist), which is why the daily lineup job was a no-op and lineups stayed as
placeholder/seed data.

Each source's config feeds lineup_adapter.TicketmasterLineupAdapter:
  {festival_slug, tm_keyword, year, headliners_per_day}
The adapter already name-filters (only real festival-day events with ≥5 billed
acts produce rows), so seeding a festival that ISN'T on Ticketmaster is harmless —
it simply yields zero lineup rows (honest "lineup TBA").

Only seeds sources for festivals that EXIST in the festivals table (slug match) so
lineups link. Idempotent: upserts on the source slug.

Run:
    python seed_lineup_sources.py            # flagship + major tiers
    python seed_lineup_sources.py --all      # every tier in the CSV
    python seed_lineup_sources.py --dry-run
"""

from __future__ import annotations

import os
import csv
import argparse

from dotenv import load_dotenv
from supabase import create_client, Client
from rich.console import Console

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
console = Console()
_CSV = os.path.join(os.path.dirname(__file__), "festival_targets.csv")
YEAR = 2026


def get_supabase() -> Client:
    return create_client(os.environ["NEXT_PUBLIC_SUPABASE_URL"],
                         os.environ["SUPABASE_SERVICE_ROLE_KEY"])


def main() -> None:
    p = argparse.ArgumentParser(description="Seed ticketmaster_lineup sources from festival_targets.csv")
    p.add_argument("--all", action="store_true", help="all tiers (default: flagship + major only)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    sb = get_supabase()
    existing_slugs = {f["slug"] for f in sb.table("festivals").select("slug").execute().data}

    with open(_CSV, newline="", encoding="utf-8") as fh:
        targets = list(csv.DictReader(fh))

    tiers = None if args.all else {"flagship", "major"}
    rows: list[dict] = []
    skipped_no_fest, skipped_no_kw = [], []
    for t in targets:
        slug = (t.get("slug") or "").strip()
        kw = (t.get("tm_keyword") or "").strip()
        tier = (t.get("tier") or "").strip()
        if tiers and tier not in tiers:
            continue
        if not kw:
            skipped_no_kw.append(slug); continue
        if slug not in existing_slugs:
            skipped_no_fest.append(slug); continue
        rows.append({
            "slug": f"{slug}-lineup-tm",
            "name": f"{t.get('name', slug)} lineup (Ticketmaster)",
            "adapter_type": "api",
            "adapter_key": "ticketmaster_lineup",
            "config": {"festival_slug": slug, "tm_keyword": kw,
                       "year": YEAR, "headliners_per_day": 2},
            "trust": "ticketmaster",
            "enabled": True,
        })

    console.log(f"[cyan]{len(rows)} lineup sources to seed "
                f"(skipped: {len(skipped_no_fest)} no-festival, {len(skipped_no_kw)} no-keyword)")
    if skipped_no_fest:
        console.log(f"[dim]no festival row for: {', '.join(skipped_no_fest[:12])}"
                    f"{' …' if len(skipped_no_fest) > 12 else ''}")
    if args.dry_run:
        for r in rows:
            console.log(f"  • {r['slug']} → {r['config']['festival_slug']} (kw={r['config']['tm_keyword']})")
        return

    for i in range(0, len(rows), 100):
        sb.table("sources").upsert(rows[i:i+100], on_conflict="slug").execute()
    console.log(f"[green]Seeded/updated {len(rows)} ticketmaster_lineup sources.")


if __name__ == "__main__":
    main()
