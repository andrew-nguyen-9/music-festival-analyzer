"""
fun_facts_generator.py
----------------------
Uses the Anthropic Claude API to generate fun, shareable facts about a
festival's current lineup. Facts are stored in the fun_facts table and
served on each festival page.

Run:
    python fun_facts_generator.py --festival lollapalooza --year 2026
    python fun_facts_generator.py --all --year 2026   # all active festivals

Schedule: Triggered by artist_enricher.py when lineup data changes,
          or manually on lineup announcement.
"""

import os
import json
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

import anthropic
from supabase import create_client, Client
from rich.console import Console

load_dotenv()
console = Console()
log = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """You are a music journalist and festival expert with deep knowledge of
artist histories, genre crossovers, cultural moments, and festival lore.
You generate fun, shareable, and surprising facts about music festival lineups.
Facts should be specific, accurate, and genuinely interesting — not generic.
Always respond with valid JSON only, no markdown, no preamble."""

FACT_CATEGORIES = [
    "debut_or_return",       # First time at this festival / comeback
    "genre_crossover",       # Surprising genre mix in the lineup
    "combined_streams",      # Aggregate streaming stat
    "geography",             # Where artists are from
    "career_milestone",      # Grammy wins, chart records, etc.
    "connection",            # Artists who have collaborated or share history
    "headliner_history",     # Headliner's relationship with the festival
    "surprising_pairing",    # Two artists you wouldn't expect on the same bill
]


def get_supabase() -> Client:
    return create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )


def get_lineup_context(supabase: Client, festival_slug: str, year: int) -> dict:
    """Pulls full lineup + artist metadata for the prompt."""
    festival = supabase.table("festivals").select("*").eq("slug", festival_slug).single().execute().data

    lineups = (
        supabase.table("lineups")
        .select("*, artists(*)")
        .eq("festival_id", festival["id"])
        .eq("year", year)
        .execute()
        .data
    )

    artists = [row["artists"] for row in lineups if row.get("artists")]
    headliners = [row["artists"]["name"] for row in lineups if row.get("is_headliner") and row.get("artists")]

    return {
        "festival": festival,
        "artists": artists,
        "headliners": headliners,
        "lineup_count": len(artists),
    }


def build_prompt(context: dict, year: int) -> str:
    festival = context["festival"]
    artists = context["artists"]
    headliners = context["headliners"]

    artist_summaries = []
    for a in artists[:80]:  # cap at 80 to stay within context
        genres = ", ".join(a.get("genres", [])[:3]) or "unknown genre"
        followers = f"{a.get('spotify_followers', 0):,}" if a.get("spotify_followers") else "unknown"
        summary = f"- {a['name']} ({genres}, {followers} Spotify followers)"
        artist_summaries.append(summary)

    artist_list = "\n".join(artist_summaries)

    return f"""Generate 8 fun facts about the {year} {festival['name']} lineup.

Festival: {festival['name']}
Location: {festival.get('city')}, {festival.get('state')}
Year: {year}
Headliners: {', '.join(headliners) if headliners else 'unknown'}
Total artists: {context['lineup_count']}

Artist roster:
{artist_list}

Return a JSON array of exactly 8 objects. Each object must have:
- "fact": string (the fun fact, 1-2 sentences, specific and interesting)
- "category": string (one of: {', '.join(FACT_CATEGORIES)})
- "artists_mentioned": array of artist name strings referenced in the fact

Example format:
[
  {{
    "fact": "This year marks Hozier's first Lollapalooza headline slot, 10 years after he debuted on the smallest stage in 2014.",
    "category": "headliner_history",
    "artists_mentioned": ["Hozier"]
  }}
]

Focus on: debut appearances, surprising genre crossovers, record-breaking streaming numbers,
geographic diversity, career milestones, and unexpected artist connections. Be specific — cite
actual chart positions, Spotify numbers, Grammy counts, or years where possible."""


def generate_fun_facts(festival_slug: str, year: int) -> list[dict]:
    supabase = get_supabase()
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    console.log(f"[cyan]Pulling lineup context for {festival_slug} {year}...")
    context = get_lineup_context(supabase, festival_slug, year)

    if not context["artists"]:
        console.log(f"[red]No artists found for {festival_slug} {year}")
        return []

    console.log(f"[cyan]Generating fun facts via Claude ({CLAUDE_MODEL})...")
    prompt = build_prompt(context, year)

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()

    try:
        facts = json.loads(raw)
        console.log(f"[green]Generated {len(facts)} fun facts")
    except json.JSONDecodeError as e:
        log.error(f"Failed to parse Claude response as JSON: {e}\nRaw: {raw[:200]}")
        return []

    # Store in Supabase
    festival = context["festival"]
    record = {
        "festival_id": festival["id"],
        "year": year,
        "facts": facts,
        "model_version": CLAUDE_MODEL,
        "generated_at": datetime.utcnow().isoformat(),
    }

    supabase.table("fun_facts").upsert(
        record, on_conflict="festival_id,year"
    ).execute()

    console.log(f"[green]Stored fun facts for {festival['name']} {year}")
    return facts


def main():
    parser = argparse.ArgumentParser(description="Generate AI fun facts for festival lineups")
    parser.add_argument("--festival", type=str, help="Festival slug (e.g. lollapalooza)")
    parser.add_argument("--year", type=int, default=datetime.now().year, help="Lineup year")
    parser.add_argument("--all", action="store_true", help="Run for all active festivals")
    args = parser.parse_args()

    if args.all:
        supabase = get_supabase()
        festivals = supabase.table("festivals").select("slug").eq("is_active", True).execute().data
        for f in festivals:
            try:
                generate_fun_facts(f["slug"], args.year)
            except Exception as e:
                log.error(f"Failed for {f['slug']}: {e}")
        return

    if not args.festival:
        parser.error("--festival or --all is required")

    facts = generate_fun_facts(args.festival, args.year)
    for i, f in enumerate(facts, 1):
        console.print(f"[bold]{i}.[/bold] {f['fact']}")


if __name__ == "__main__":
    main()
