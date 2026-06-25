-- Migration: 20260625_v3_0_1_source_registry_and_run_log  (v3.0.1)
-- Foundation for v3's ingestion framework: a source REGISTRY + a per-run LOG,
-- plus per-row provenance on lineups. Additive + idempotent; safe to re-run.
-- Run in the Supabase SQL editor (service role).
--
-- Why: v2 hand-codes one Python script per source (Wikipedia, Songkick, …),
-- each re-implementing client + retry + upsert. v3.0 replaces that fork with a
-- SourceAdapter contract (v3.0.2). This migration gives that contract its two
-- backing tables — what sources exist (`sources`) and what each run did
-- (`ingestion_runs`) — and lets a lineup row point back at the source that
-- wrote it (`lineups.source_id`). The existing trust triggers from v2.3.3
-- (protect_verified_lineups / skip_unverified_insert) still referee conflicts;
-- this only adds provenance, it does not change the conflict policy.

-- ── sources: the ingestion source registry ─────────────────────
-- One row per ingestion source. `adapter_key` maps to a Python adapter class in
-- the v3.0.2 registry; `adapter_type` is the coarse kind. `config` carries
-- per-source params (URLs, API ids, festival scope) so adding a source is a row,
-- not a code fork. `trust` is the provenance label rows from this source get
-- (same vocab as lineups.source: official|wikipedia|ticketmaster|songkick|
-- setlistfm|ocr|estimated) — kept free text (not a CHECK) so the vocab can grow.
create table if not exists sources (
  id           uuid primary key default uuid_generate_v4(),
  slug         text unique not null,                 -- 'wikipedia-us-festivals', 'lolla-official-poster'
  name         text not null,
  adapter_type text not null check (adapter_type in ('scrape', 'api', 'manual')),
  adapter_key  text not null,                        -- registry key → SourceAdapter subclass
  config       jsonb not null default '{}'::jsonb,   -- per-source params (urls, api ids, festival scope)
  trust        text,                                 -- provenance label rows get; see lineups.source vocab
  enabled      boolean not null default true,
  schedule     text,                                 -- optional cron hint for the daily/weekly runner
  created_at   timestamptz default now(),
  updated_at   timestamptz default now()
);

-- ── ingestion_runs: the run-log (observability) ────────────────
-- One row per adapter invocation. The v3.0.2 orchestrator opens a row at start
-- (status 'running'), and closes it with counts + any per-stage errors. This is
-- the spine v3.11 dashboards + v3.8 change-detection read from. `festival_slug`
-- is null for catalog-wide runs (e.g. the Wikipedia list scrape).
create table if not exists ingestion_runs (
  id             uuid primary key default uuid_generate_v4(),
  source_id      uuid references sources(id) on delete set null,
  festival_slug  text,                               -- null = catalog-wide run
  status         text not null default 'running'
                   check (status in ('running', 'success', 'error', 'partial')),
  started_at     timestamptz not null default now(),
  finished_at    timestamptz,
  rows_upserted  int not null default 0,
  rows_skipped   int not null default 0,             -- e.g. dropped by the verified-row triggers
  errors         jsonb not null default '[]'::jsonb, -- [{stage, message}]
  stats          jsonb not null default '{}'::jsonb, -- adapter-specific counters
  created_at     timestamptz default now()
);

-- Recent-runs-per-source lookup (dashboards, "is this source stale?").
create index if not exists idx_ingestion_runs_source_started
  on ingestion_runs (source_id, started_at desc);
-- Freshness-per-festival lookup (v3.1 freshness gate).
create index if not exists idx_ingestion_runs_festival_started
  on ingestion_runs (festival_slug, started_at desc) where festival_slug is not null;

-- ── lineups: per-row provenance ────────────────────────────────
-- v2.3.3 added lineups.source (the trust *label*). v3.0 adds source_id (which
-- *registry row* wrote it) + confidence (0..1), so v3.2's per-source conflict
-- resolution has a key to coalesce-forward on. Nullable + ON DELETE SET NULL:
-- dropping a source must not cascade-delete real lineup rows.
alter table lineups add column if not exists source_id  uuid references sources(id) on delete set null;
alter table lineups add column if not exists confidence real;  -- 0.0–1.0; null = unscored

-- ── RLS: public read, service-role write (matches every other table) ──
alter table sources        enable row level security;
alter table ingestion_runs enable row level security;

drop policy if exists "Public read sources"        on sources;
drop policy if exists "Public read ingestion_runs" on ingestion_runs;
create policy "Public read sources"        on sources        for select using (true);
create policy "Public read ingestion_runs" on ingestion_runs for select using (true);

-- ── updated_at trigger (reuse the existing set_updated_at()) ───
drop trigger if exists sources_updated_at on sources;
create trigger sources_updated_at before update on sources
  for each row execute function set_updated_at();

-- ── Rollback ───────────────────────────────────────────────────
-- alter table lineups drop column if exists confidence;
-- alter table lineups drop column if exists source_id;
-- drop table if exists ingestion_runs;
-- drop table if exists sources;
