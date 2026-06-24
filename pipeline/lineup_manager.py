"""
lineup_manager.py
-----------------
CLI tool for viewing and cleaning up lineup entries in Supabase.
Use this to remove test / seed data and fix incorrect lineup entries.

Commands:
    # List all lineup entries for a festival
    python lineup_manager.py --list --festival lollapalooza --year 2026

    # Remove one artist from a festival lineup (keeps the artist record)
    python lineup_manager.py --remove-artist hozier --festival lollapalooza --year 2026

    # Remove multiple artists at once
    python lineup_manager.py --remove-artist hozier chappell-roan --festival lollapalooza --year 2026

    # Clear ALL lineup entries for a festival/year (then re-run lineup_scraper)
    python lineup_manager.py --clear --festival lollapalooza --year 2026

    # Show artists that have no lineup entries anywhere (orphans from seed/test data)
    python lineup_manager.py --list-orphans

    # Delete all orphan artists (with confirmation)
    python lineup_manager.py --delete-orphans --force
"""

import os
import argparse
import logging
from slugify import slugify
from dotenv import load_dotenv

from supabase import create_client, Client
from rich.console import Console
from rich.table import Table

load_dotenv()
console = Console()
log = logging.getLogger(__name__)


def get_supabase() -> Client:
    return create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def resolve_festival(supabase: Client, slug: str) -> dict | None:
    r = supabase.table("festivals").select("id, name, slug").eq("slug", slug).execute()
    return r.data[0] if r.data else None


# ── List ──────────────────────────────────────────────────────

def list_lineup(supabase: Client, festival_slug: str, year: int) -> None:
    festival = resolve_festival(supabase, festival_slug)
    if not festival:
        console.log(f"[red]Festival not found: {festival_slug}")
        return

    rows = (
        supabase.table("lineups")
        .select("id, year, day, stage, set_time_start, set_time_end, is_headliner, artists(slug, name)")
        .eq("festival_id", festival["id"])
        .eq("year", year)
        .order("day")
        .execute()
        .data
    )

    if not rows:
        console.log(f"[yellow]No lineup entries for {festival['name']} {year}")
        return

    table = Table(title=f"{festival['name']} {year} Lineup ({len(rows)} entries)")
    table.add_column("Artist", style="white")
    table.add_column("Slug", style="dim")
    table.add_column("Day")
    table.add_column("Stage")
    table.add_column("Time")
    table.add_column("H")

    for row in rows:
        artist = row.get("artists") or {}
        day   = row.get("day") or ""
        stage = (row.get("stage") or "")[:20]
        t     = row.get("set_time_start") or ""
        h     = "★" if row.get("is_headliner") else " "
        table.add_row(artist.get("name", "?"), artist.get("slug", "?"), day, stage, t, h)

    console.print(table)


# ── Remove artist from lineup ─────────────────────────────────

def remove_artist_from_lineup(
    supabase: Client,
    festival_slug: str,
    artist_slugs: list[str],
    year: int,
    force: bool,
) -> None:
    festival = resolve_festival(supabase, festival_slug)
    if not festival:
        console.log(f"[red]Festival not found: {festival_slug}")
        return

    for artist_slug in artist_slugs:
        artist_r = supabase.table("artists").select("id, name").eq("slug", artist_slug).execute()
        if not artist_r.data:
            console.log(f"[yellow]Artist not found: {artist_slug}")
            continue
        artist = artist_r.data[0]

        lineup_r = (
            supabase.table("lineups")
            .select("id")
            .eq("festival_id", festival["id"])
            .eq("artist_id", artist["id"])
            .eq("year", year)
            .execute()
        )
        if not lineup_r.data:
            console.log(f"[yellow]{artist['name']}: not in {festival['name']} {year} lineup")
            continue

        if not force:
            console.log(
                f"[yellow]Would remove [bold]{artist['name']}[/bold] from "
                f"{festival['name']} {year}. Pass --force to confirm."
            )
            continue

        supabase.table("lineups").delete().eq("id", lineup_r.data[0]["id"]).execute()
        console.log(f"[green]Removed {artist['name']} from {festival['name']} {year}")


# ── Clear entire lineup ───────────────────────────────────────

def clear_lineup(supabase: Client, festival_slug: str, year: int, force: bool) -> None:
    festival = resolve_festival(supabase, festival_slug)
    if not festival:
        console.log(f"[red]Festival not found: {festival_slug}")
        return

    count_r = (
        supabase.table("lineups")
        .select("id", count="exact")
        .eq("festival_id", festival["id"])
        .eq("year", year)
        .execute()
    )
    n = count_r.count or 0

    if n == 0:
        console.log(f"[yellow]No lineup entries for {festival['name']} {year}")
        return

    if not force:
        console.log(
            f"[yellow]Would delete [bold]{n}[/bold] lineup entries for "
            f"{festival['name']} {year}. Pass --force to confirm."
        )
        return

    supabase.table("lineups").delete().eq("festival_id", festival["id"]).eq("year", year).execute()
    console.log(f"[green]Deleted {n} lineup entries for {festival['name']} {year}")


# ── Orphan artists ────────────────────────────────────────────

def list_orphans(supabase: Client) -> list[dict]:
    all_artists = supabase.table("artists").select("id, slug, name, created_at").order("name").execute().data
    linked_ids = {
        row["artist_id"]
        for row in supabase.table("lineups").select("artist_id").execute().data
    }
    orphans = [a for a in all_artists if a["id"] not in linked_ids]

    if not orphans:
        console.log("[green]No orphan artists found.")
        return []

    table = Table(title=f"Orphan Artists ({len(orphans)} — no lineup entries)")
    table.add_column("Name", style="white")
    table.add_column("Slug", style="dim")
    table.add_column("Created", style="dim")
    for a in orphans:
        table.add_row(a["name"], a["slug"], (a.get("created_at") or "")[:10])
    console.print(table)
    return orphans


def delete_orphans(supabase: Client, force: bool) -> None:
    orphans = list_orphans(supabase)
    if not orphans:
        return
    if not force:
        console.log(f"[yellow]Pass --force to delete {len(orphans)} orphan artists.")
        return
    for a in orphans:
        supabase.table("artists").delete().eq("id", a["id"]).execute()
    console.log(f"[green]Deleted {len(orphans)} orphan artists.")


# ── Main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Manage festival lineup entries in Supabase")
    parser.add_argument("--festival",  type=str, help="Festival slug")
    parser.add_argument("--year",      type=int, default=2026)
    parser.add_argument("--force",     action="store_true", help="Execute destructive operations")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list",          action="store_true",  help="List lineup for festival/year")
    group.add_argument("--remove-artist", type=str, nargs="+",  metavar="SLUG",
                       help="Remove artist(s) from lineup (by artist slug)")
    group.add_argument("--clear",         action="store_true",  help="Clear all lineup entries for festival/year")
    group.add_argument("--list-orphans",  action="store_true",  help="List artists with no lineup entries")
    group.add_argument("--delete-orphans",action="store_true",  help="Delete all orphan artists (use with --force)")

    args = parser.parse_args()
    supabase = get_supabase()

    if args.list:
        if not args.festival:
            parser.error("--list requires --festival")
        list_lineup(supabase, args.festival, args.year)

    elif args.remove_artist:
        if not args.festival:
            parser.error("--remove-artist requires --festival")
        slugs = [slugify(s) if not s.replace("-", "").isalnum() else s for s in args.remove_artist]
        remove_artist_from_lineup(supabase, args.festival, slugs, args.year, args.force)

    elif args.clear:
        if not args.festival:
            parser.error("--clear requires --festival")
        clear_lineup(supabase, args.festival, args.year, args.force)

    elif args.list_orphans:
        list_orphans(supabase)

    elif args.delete_orphans:
        delete_orphans(supabase, args.force)


if __name__ == "__main__":
    main()
