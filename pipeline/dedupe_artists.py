"""
dedupe_artists.py
-----------------
Read-only report of artist-row data-quality problems that the v2.3.1 audit
identified. It NEVER merges or rewrites rows on its own: merging two `artists`
rows means reassigning `lineups.artist_id` and `artist_spotify_cache.artist_id`
FKs, which is unsafe to do unattended in a daily cron. Instead it prints what to
fix and the SQL to do it, for a human to run once.

Two problem classes:
  1. duplicate group  — >1 distinct artist row sharing one canonical slug
                        (e.g. a name written by two scripts before v2.3.2).
  2. mangled slug     — a row whose stored slug != canonical_slug(name)
                        (the pre-v2.3 accent bug: "Röz" stored as "r-z").

Run:
    python dedupe_artists.py            # print the report
    python dedupe_artists.py --json     # machine-readable
"""

import os
import json
import argparse
from collections import defaultdict

from names import canonical_slug

# Heavy/optional deps (supabase, dotenv, rich) are imported lazily inside the DB
# functions so `--self-test` runs in CI with only python-slugify installed.


# ── Pure analysis (no DB) — unit-testable ──────────────────────

def find_duplicate_groups(artists: list[dict]) -> list[dict]:
    """Group artists by canonical slug; return groups with >1 distinct row.
    Each artist dict needs at least: id, slug, name."""
    by_canon: dict[str, list[dict]] = defaultdict(list)
    for a in artists:
        by_canon[canonical_slug(a["name"])].append(a)
    return [
        {"canonical_slug": canon, "rows": rows}
        for canon, rows in sorted(by_canon.items())
        if len({r["id"] for r in rows}) > 1
    ]


def find_mangled_slugs(artists: list[dict]) -> list[dict]:
    """Rows whose stored slug disagrees with canonical_slug(name)."""
    out = []
    for a in artists:
        want = canonical_slug(a["name"])
        if a["slug"] != want:
            out.append({"id": a["id"], "name": a["name"],
                        "stored_slug": a["slug"], "canonical_slug": want})
    return out


# ── DB + reporting ─────────────────────────────────────────────

def get_supabase():
    from dotenv import load_dotenv
    from supabase import create_client
    load_dotenv()
    return create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def load_artists(sb) -> list[dict]:
    rows: list[dict] = []
    page = 0
    while True:
        chunk = (
            sb.table("artists").select("id, slug, name, spotify_id")
            .range(page * 1000, page * 1000 + 999).execute()
        )
        if not chunk.data:
            break
        rows.extend(chunk.data)
        if len(chunk.data) < 1000:
            break
        page += 1
    return rows


def main() -> None:
    from rich.console import Console
    from rich.table import Table
    console = Console()

    parser = argparse.ArgumentParser(description="Report artist-row duplicates / mangled slugs")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    artists = load_artists(get_supabase())
    dupes = find_duplicate_groups(artists)
    mangled = find_mangled_slugs(artists)

    if args.json:
        print(json.dumps({"duplicate_groups": dupes, "mangled_slugs": mangled}, indent=2))
        return

    console.rule(f"[bold]Artist dedupe report — {len(artists)} rows")

    if dupes:
        t = Table(title=f"{len(dupes)} duplicate group(s)")
        t.add_column("canonical slug", style="cyan")
        t.add_column("rows (id · slug · name)")
        for g in dupes:
            t.add_row(g["canonical_slug"],
                      "\n".join(f"{r['id'][:8]} · {r['slug']} · {r['name']}" for r in g["rows"]))
        console.print(t)
        console.print("[yellow]Merge manually: keep the row with a spotify_id / cache, "
                      "repoint lineups.artist_id + artist_spotify_cache.artist_id, then delete the other.[/yellow]")
    else:
        console.print("[green]No duplicate groups.[/green]")

    if mangled:
        t = Table(title=f"{len(mangled)} mangled slug(s) — pre-v2.3.2 writes")
        t.add_column("name", style="bold")
        t.add_column("stored", style="red")
        t.add_column("canonical", style="green")
        for m in mangled:
            t.add_row(m["name"], m["stored_slug"], m["canonical_slug"])
        console.print(t)
        console.print("[yellow]Fix with: update artists set slug = <canonical> where id = <id>; "
                      "(check it doesn't collide with an existing row first).[/yellow]")
    else:
        console.print("[green]No mangled slugs.[/green]")


def _demo() -> None:
    sample = [
        {"id": "1", "slug": "roz", "name": "Röz"},        # canonical
        {"id": "2", "slug": "r-z", "name": "Röz"},        # mangled dup of #1
        {"id": "3", "slug": "wet-leg", "name": "Wet Leg"},
    ]
    groups = find_duplicate_groups(sample)
    assert len(groups) == 1 and groups[0]["canonical_slug"] == "roz", groups
    assert {r["id"] for r in groups[0]["rows"]} == {"1", "2"}
    mangled = find_mangled_slugs(sample)
    assert [m["id"] for m in mangled] == ["2"], mangled
    print("dedupe_artists: all checks passed")


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        _demo()
    else:
        main()
