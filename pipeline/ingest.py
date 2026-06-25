"""
ingest.py — v3.0 ingestion framework
------------------------------------
One SourceAdapter contract + one run() orchestrator. v2 hand-codes a script per
source, each re-implementing client + retry + upsert; this collapses that
plumbing into a single place. Adapters only *parse* (fetch → normalize); the
orchestrator owns validate → upsert and writes the ingestion_runs run-log. The
v2.3.3 DB triggers still referee trust conflicts — nothing here overrides them.

Adding a festival is a `sources` row, not a code fork: the built-in
`manual_config` adapter takes its festival + lineup payload straight from the
registry row's `config` jsonb (see db/seed_sources.sql). Scrape/API adapters
subclass SourceAdapter the same way and land in v3.2.

Run:
    python ingest.py --source lolla-official     # one source by slug
    python ingest.py --festival lollapalooza     # all enabled sources for a festival
    python ingest.py --self-test                 # offline asserts, no DB/network
"""

from __future__ import annotations

import os
import argparse
import logging
import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.console import Console

load_dotenv()
console = Console()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


# ── Normalized adapter output ──────────────────────────────────
# Lineups carry artist_slug/festival_slug (+ optional artist_name); the
# orchestrator resolves those to FK ids after upserting festivals/artists.
@dataclass
class Normalized:
    festivals: list[dict] = field(default_factory=list)
    artists: list[dict] = field(default_factory=list)
    lineups: list[dict] = field(default_factory=list)


# ── Adapter contract + registry ────────────────────────────────
class SourceAdapter(ABC):
    key: str = ""            # registry key; matches sources.adapter_key
    trust: str | None = None  # default provenance label for rows (lineups.source vocab)
    festival_merge: str | None = None  # 'coalesce' → run() trust-merges festival rows (v3.2)

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    @abstractmethod
    def fetch(self):
        """Pull raw payload from the source (network/file/registry config)."""

    @abstractmethod
    def normalize(self, raw) -> Normalized:
        """Map raw payload → Normalized rows. Parsing lives here, nothing else."""


_REGISTRY: dict[str, type[SourceAdapter]] = {}


def register(cls):
    _REGISTRY[cls.key] = cls
    return cls


def get_adapter(key: str, config: dict | None = None) -> SourceAdapter:
    if key not in _REGISTRY:
        raise KeyError(f"no adapter for key={key!r}; known={sorted(_REGISTRY)}")
    return _REGISTRY[key](config)


# ── Shared Supabase client (finally DRY across the pipeline) ────
def get_supabase():
    from supabase import create_client
    return create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


# ── Store seam: real (Supabase) + a fake for the self-test ─────
# A thin data-access boundary so run() is testable without a DB. Two impls
# (SupabaseStore + the test's fake) justify the seam — it's not a 1-impl interface.
class SupabaseStore:
    def __init__(self, client):
        self.c = client

    def open_run(self, source_id, festival_slug) -> str:
        row = (
            self.c.table("ingestion_runs")
            .insert({"source_id": source_id, "festival_slug": festival_slug, "status": "running"})
            .execute()
            .data[0]
        )
        return row["id"]

    def close_run(self, run_id, status, rows_upserted, rows_skipped, errors, stats):
        self.c.table("ingestion_runs").update({
            "status": status,
            "finished_at": _now(),
            "rows_upserted": rows_upserted,
            "rows_skipped": rows_skipped,
            "errors": errors,
            "stats": stats,
        }).eq("id", run_id).execute()

    def upsert(self, table, rows, on_conflict) -> list[dict]:
        if not rows:
            return []
        return self.c.table(table).upsert(rows, on_conflict=on_conflict).execute().data

    def resolve_ids(self, table, slugs) -> dict:
        if not slugs:
            return {}
        rows = self.c.table(table).select("id, slug").in_("slug", list(slugs)).execute().data
        return {r["slug"]: r["id"] for r in rows}

    def merge_festivals(self, rows, trust) -> list[dict]:
        """Coalesce-forward festival merge (v3.2): fill missing fields + replace
        *estimated* dates, but never clobber curated/official metadata. Reads the
        existing row per slug, applies merge_festival_fields, and insert/updates.
        `trust` is reserved for a future per-field provenance check (see ponytail note)."""
        affected: list[dict] = []
        for r in rows:
            existing = (self.c.table("festivals")
                        .select("start_date, end_date, dates_estimated, "
                                "latitude, longitude, venue, city, state, timezone")
                        .eq("slug", r["slug"]).execute().data)
            op, payload = merge_festival_fields(existing[0] if existing else None, r)
            if op == "insert":
                affected += self.c.table("festivals").insert(payload).execute().data
            elif op == "update":
                payload["updated_at"] = _now()
                affected += (self.c.table("festivals")
                             .update(payload).eq("slug", r["slug"]).execute().data)
        return affected


# ── Validation ─────────────────────────────────────────────────
_REQUIRED = {
    "festivals": ("slug", "name"),
    "artists": ("slug", "name"),
    "lineups": ("festival_slug", "artist_slug", "year"),
}


def _valid(rows: list[dict], required: tuple) -> tuple[list[dict], int]:
    """Keep rows with all required fields; return (kept, dropped_count)."""
    kept = [r for r in rows if all(r.get(k) not in (None, "") for k in required)]
    return kept, len(rows) - len(kept)


def _derive_artists(lineups: list[dict], explicit: list[dict]) -> list[dict]:
    """Auto-build minimal artist rows from lineup entries (slug + name)."""
    out = list(explicit)
    seen = {a.get("slug") for a in out}
    for ln in lineups:
        slug, name = ln.get("artist_slug"), ln.get("artist_name")
        if slug and name and slug not in seen:
            out.append({"slug": slug, "name": name})
            seen.add(slug)
    return out


# Aggregator-sourced festival fields that may be FILLED when missing (never overwritten).
_AGG_FILL = ("latitude", "longitude", "venue", "city", "state", "timezone")


def merge_festival_fields(existing: dict | None, incoming: dict) -> tuple[str, dict]:
    """Coalesce-forward, trust-ordered festival merge (pure → testable offline).

    - new row (existing is None) → insert the non-null incoming fields; real dates
      clear the dates_estimated flag.
    - dates → replace iff the row has none OR is flagged dates_estimated (a stub);
      never overwrite curated/official dates.
    - _AGG_FILL fields → fill only when the existing value is null/empty.
    - everything else (name, accent_color, tags, website_url, …) is left untouched.
    Returns ('insert'|'update'|'noop', payload)."""
    if existing is None:
        payload = {k: v for k, v in incoming.items() if v is not None}
        if incoming.get("start_date") and incoming.get("end_date"):
            payload["dates_estimated"] = False
        return "insert", payload

    upd: dict = {}
    if incoming.get("start_date") and incoming.get("end_date") and (
            not existing.get("start_date") or existing.get("dates_estimated")):
        upd["start_date"] = incoming["start_date"]
        upd["end_date"] = incoming["end_date"]
        upd["dates_estimated"] = False
    for k in _AGG_FILL:
        if incoming.get(k) is not None and not existing.get(k):
            upd[k] = incoming[k]
    return ("update", upd) if upd else ("noop", {})


_LINEUP_COLS = ("year", "stage", "day", "set_time_start", "set_time_end", "is_headliner")


def _lineup_rows(lineups, fest_ids, art_ids, source_id, trust) -> tuple[list[dict], int]:
    """Resolve festival/artist slugs → FK ids; drop (count) the unresolved."""
    rows, dropped = [], 0
    for ln in lineups:
        fid = fest_ids.get(ln.get("festival_slug"))
        aid = art_ids.get(ln.get("artist_slug"))
        if not fid or not aid:
            dropped += 1
            continue
        row = {"festival_id": fid, "artist_id": aid, "source": trust, "source_id": source_id}
        if ln.get("confidence") is not None:
            row["confidence"] = ln["confidence"]
        for col in _LINEUP_COLS:
            if ln.get(col) is not None:
                row[col] = ln[col]
        rows.append(row)
    return rows, dropped


# ── Orchestrator ───────────────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def _fetch(adapter):
    return adapter.fetch()


def run(adapter: SourceAdapter, store, source_id=None, festival_slug=None, trust=None) -> dict:
    """fetch → normalize → validate → upsert, wrapped in an ingestion_runs row.

    rows_upserted counts rows the DB returned (so trust-trigger-skipped INSERTs
    are excluded). rows_skipped counts validation drops + unresolved-FK lineups.
    """
    trust = trust or adapter.trust
    run_id = store.open_run(source_id, festival_slug)
    errors, skipped, upserted = [], 0, 0
    try:
        norm = adapter.normalize(_fetch(adapter))

        fests, s = _valid(norm.festivals, _REQUIRED["festivals"]); skipped += s
        arts, s = _valid(_derive_artists(norm.lineups, norm.artists), _REQUIRED["artists"]); skipped += s
        lns, s = _valid(norm.lineups, _REQUIRED["lineups"]); skipped += s

        # Aggregator/low-trust sources coalesce-forward (fill, don't clobber); the
        # default path clobbers on slug as before (curated/official sources own the row).
        if adapter.festival_merge == "coalesce":
            upserted += len(store.merge_festivals(fests, trust))
        else:
            upserted += len(store.upsert("festivals", fests, "slug"))
        upserted += len(store.upsert("artists", arts, "slug"))

        fest_ids = store.resolve_ids("festivals", {l["festival_slug"] for l in lns})
        art_ids = store.resolve_ids("artists", {l["artist_slug"] for l in lns})
        lrows, s = _lineup_rows(lns, fest_ids, art_ids, source_id, trust); skipped += s
        upserted += len(store.upsert(
            "lineups", lrows, "festival_id,artist_id,year,day,set_time_start"
        ))

        status = "partial" if (errors or skipped) else "success"
    except Exception as e:  # noqa: BLE001 — any adapter failure → logged 'error' run
        log.exception("ingest run failed")
        errors.append({"stage": "run", "message": str(e)})
        status = "error"

    # Adapters may stash cross-source / parse stats on themselves (e.g. aggregator
    # provider agreement + conflict counts) → recorded in the ingestion_runs row.
    store.close_run(run_id, status, upserted, skipped, errors, getattr(adapter, "stats", {}) or {})
    console.log(f"[{'green' if status == 'success' else 'yellow'}]"
                f"{status}: +{upserted} upserted, {skipped} skipped, {len(errors)} errors")
    return {"run_id": run_id, "status": status,
            "rows_upserted": upserted, "rows_skipped": skipped, "errors": errors}


# ── Built-in adapter: config-driven manual ingest ──────────────
# The whole point of v3.0: a festival with no programmatic source is a `sources`
# row whose config holds its festival + lineup payload. Zero per-festival Python.
@register
class ConfigManualAdapter(SourceAdapter):
    key = "manual_config"
    trust = "official"

    def fetch(self):
        return self.config  # payload already lives in the registry row

    def normalize(self, raw) -> Normalized:
        fests = raw.get("festivals") or ([raw["festival"]] if raw.get("festival") else [])
        return Normalized(
            festivals=fests,
            artists=raw.get("artists", []),
            lineups=raw.get("lineups", []),
        )


# ── CLI ────────────────────────────────────────────────────────
def _run_source_row(store, row) -> dict:
    adapter = get_adapter(row["adapter_key"], row.get("config"))
    fest_slug = (row.get("config") or {}).get("festival", {}).get("slug")
    console.log(f"[cyan]Running source [bold]{row['slug']}[/bold] ({row['adapter_key']})")
    return run(adapter, store, source_id=row["id"], festival_slug=fest_slug, trust=row.get("trust"))


def main():
    parser = argparse.ArgumentParser(description="v3.0 ingestion framework runner")
    parser.add_argument("--source", help="run one enabled source by slug")
    parser.add_argument("--festival", help="run all enabled sources scoped to this festival slug")
    parser.add_argument("--self-test", action="store_true", help="offline asserts, no DB/network")
    args = parser.parse_args()

    if args.self_test:
        import test_ingest
        test_ingest.run_all()
        return

    if not (args.source or args.festival):
        parser.error("pass --source <slug>, --festival <slug>, or --self-test")

    store = SupabaseStore(get_supabase())
    q = store.c.table("sources").select("*").eq("enabled", True)
    if args.source:
        q = q.eq("slug", args.source)
    rows = q.execute().data

    if args.festival:
        # Client-side filter on the config.festival.slug convention — robust vs.
        # PostgREST jsonb-path filter quirks, and sources count is small.
        # ponytail: add a festival_slug column + index if this ever isn't cheap.
        rows = [r for r in rows
                if ((r.get("config") or {}).get("festival") or {}).get("slug") == args.festival]

    if not rows:
        console.log("[yellow]No enabled sources matched.")
        return
    for row in rows:
        _run_source_row(store, row)


if __name__ == "__main__":
    main()
