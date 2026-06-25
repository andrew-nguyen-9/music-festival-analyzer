"""
lolla_schedule_seeder.py
------------------------
Seeds the complete Lollapalooza 2026 schedule into the Supabase `lineups` table.

For each artist, the script will:
  1. Look up or create the artist record (upsert on slug)
  2. Upsert the lineup entry (on_conflict: festival_id, artist_id, year, day, set_time_start)

Run:
    python lolla_schedule_seeder.py               # seed all entries
    python lolla_schedule_seeder.py --dry-run     # preview without writing
    python lolla_schedule_seeder.py --force       # re-seed even if entries exist

Schedule: one-off / manual; re-run is safe (idempotent)
"""

import os
import argparse
import logging

from dotenv import load_dotenv
from supabase import create_client, Client
from names import canonical_name, canonical_slug
from lolla_2026_schedule import SCHEDULE, FESTIVAL_SLUG, YEAR
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich import print as rprint

load_dotenv()
console = Console()
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_supabase() -> Client:
    return create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def get_festival_id(supabase: Client) -> str:
    """Return the UUID for the lollapalooza festival row."""
    resp = (
        supabase.table("festivals")
        .select("id")
        .eq("slug", FESTIVAL_SLUG)
        .single()
        .execute()
    )
    if not resp.data:
        raise RuntimeError(
            f"Festival '{FESTIVAL_SLUG}' not found in the festivals table. "
            "Run festival_scraper.py first."
        )
    return resp.data["id"]


def upsert_artist(supabase: Client, name: str, dry_run: bool) -> str | None:
    """
    Upsert an artist record and return its UUID.
    On dry-run, returns None (no DB write).
    """
    slug = canonical_slug(name)
    if dry_run:
        return None

    resp = (
        supabase.table("artists")
        .upsert(
            {"slug": slug, "name": canonical_name(name), "genres": [], "tags": []},
            on_conflict="slug",
        )
        .execute()
    )
    if not resp.data:
        raise RuntimeError(f"Failed to upsert artist '{name}'")

    # Fetch back the ID (upsert may or may not return it depending on Supabase version)
    fetch = (
        supabase.table("artists")
        .select("id")
        .eq("slug", slug)
        .single()
        .execute()
    )
    if not fetch.data:
        raise RuntimeError(f"Could not fetch artist ID for slug '{slug}'")
    return fetch.data["id"]


def upsert_lineup_entry(
    supabase: Client,
    festival_id: str,
    artist_id: str,
    entry: dict,
    dry_run: bool,
) -> None:
    """Upsert a single lineup row."""
    row = {
        "festival_id": festival_id,
        "artist_id": artist_id,
        "year": YEAR,
        "stage": entry["stage"],
        "day": entry["day"],
        "set_time_start": entry["start"],
        "set_time_end": entry["end"],
        "is_headliner": entry["headliner"],
        "source": "official",  # hand-curated official poster — verified
    }
    if dry_run:
        return

    supabase.table("lineups").upsert(
        row,
        on_conflict="festival_id,artist_id,year,day,set_time_start",
    ).execute()


def check_existing_entries(supabase: Client, festival_id: str) -> int:
    """Return count of existing lineup entries for this festival/year."""
    resp = (
        supabase.table("lineups")
        .select("id", count="exact")
        .eq("festival_id", festival_id)
        .eq("year", YEAR)
        .execute()
    )
    return resp.count or 0


def delete_all_entries(supabase: Client, festival_id: str) -> int:
    """Delete ALL lineup rows for this festival/year and return the deleted count."""
    resp = (
        supabase.table("lineups")
        .delete()
        .eq("festival_id", festival_id)
        .eq("year", YEAR)
        .execute()
    )
    return len(resp.data) if resp.data else 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the Lollapalooza 2026 schedule into the lineups table."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview all entries without writing to the database.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-seed even if lineup entries already exist for this festival/year.",
    )
    args = parser.parse_args()

    console.rule("[bold cyan]Lollapalooza 2026 Schedule Seeder[/bold cyan]")

    if args.dry_run:
        console.print("[yellow]DRY RUN — no changes will be written to the database.[/yellow]\n")

    supabase = get_supabase()

    # 1. Resolve festival ID
    console.print(f"[dim]Looking up festival:[/dim] [bold]{FESTIVAL_SLUG}[/bold]")
    festival_id = get_festival_id(supabase) if not args.dry_run else "DRY-RUN-FESTIVAL-ID"
    console.print(f"[green]Festival ID:[/green] {festival_id}\n")

    # 2. Guard against accidental re-seeding — or wipe + replace if --force
    if not args.dry_run:
        existing = check_existing_entries(supabase, festival_id)
        if existing > 0 and not args.force:
            console.print(
                f"[yellow]Found {existing} existing lineup entries for {FESTIVAL_SLUG} {YEAR}.[/yellow]\n"
                "[yellow]Use --force to wipe them and re-seed from the canonical schedule.[/yellow]"
            )
            return
        if existing > 0 and args.force:
            console.print(f"[yellow]Wiping {existing} existing entries…[/yellow]")
            deleted = delete_all_entries(supabase, festival_id)
            console.print(f"[green]Deleted {deleted} old entries. Re-seeding from scratch.[/green]\n")

    # 3. Build a preview table for dry-run
    if args.dry_run:
        table = Table(title=f"Schedule preview — {len(SCHEDULE)} slots", show_lines=False)
        table.add_column("Day", style="cyan", no_wrap=True)
        table.add_column("Stage", style="magenta")
        table.add_column("Artist", style="bold white")
        table.add_column("Start")
        table.add_column("End")
        table.add_column("Headliner", justify="center")
        for entry in SCHEDULE:
            table.add_row(
                entry["day"],
                entry["stage"],
                entry["name"],
                entry["start"],
                entry["end"],
                "[green]YES[/green]" if entry["headliner"] else "",
            )
        console.print(table)
        console.print(f"\n[bold green]Dry run complete.[/bold green] {len(SCHEDULE)} entries would be seeded.")
        return

    # 4. Seed
    errors: list[str] = []
    inserted = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("[cyan]Seeding schedule…", total=len(SCHEDULE))

        for entry in SCHEDULE:
            artist_name = entry["name"]
            progress.update(task, description=f"[cyan]{artist_name[:40]}")
            try:
                artist_id = upsert_artist(supabase, artist_name, dry_run=False)
                upsert_lineup_entry(supabase, festival_id, artist_id, entry, dry_run=False)
                inserted += 1
            except Exception as exc:
                errors.append(f"{artist_name}: {exc}")
                console.print(f"[red]  ERROR[/red] {artist_name} — {exc}")
            finally:
                progress.advance(task)

    # 5. Summary
    console.rule()
    console.print(f"[bold green]Done.[/bold green]  {inserted}/{len(SCHEDULE)} lineup entries upserted.")
    if errors:
        console.print(f"[bold red]{len(errors)} error(s):[/bold red]")
        for err in errors:
            console.print(f"  [red]•[/red] {err}")
    else:
        console.print("[green]No errors.[/green]")


if __name__ == "__main__":
    main()
