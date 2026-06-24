-- Migration: 20260624_v2_1_4_artist_spotify_cache  (v2.1.4)
-- External-data cache table for Spotify artist data — backing store for v2.2.
-- Additive + idempotent; safe to re-run. Run in the Supabase SQL editor.
--
-- TTL semantics: rows carry fetched_at + ttl_seconds; expires_at is GENERATED so
-- the sync worker can select stale rows with `where expires_at < now()` and the
-- frontend can read fresh rows only. Frontend reads cache; never calls Spotify.

create table if not exists artist_spotify_cache (
  id            uuid primary key default uuid_generate_v4(),
  artist_id     uuid not null unique references artists(id) on delete cascade,
  spotify_id    text,
  followers     bigint,
  popularity    int,                                 -- 0–100
  genres        text[] default '{}',
  image_url     text,
  preview_url   text,                                -- 30s preview
  top_tracks    jsonb,                               -- [{name, preview_url, ...}]
  raw           jsonb,                               -- full Spotify payload (forward-compat)
  fetched_at    timestamptz not null default now(),
  ttl_seconds   int not null default 604800,         -- 7 days
  expires_at    timestamptz
                  generated always as
                  (fetched_at + make_interval(secs => ttl_seconds)) stored,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

-- Stale-row sweeps + freshness filters.
create index if not exists idx_artist_spotify_cache_expires
  on artist_spotify_cache (expires_at);

-- updated_at maintenance (reuses set_updated_at() from schema.sql).
drop trigger if exists artist_spotify_cache_updated_at on artist_spotify_cache;
create trigger artist_spotify_cache_updated_at before update on artist_spotify_cache
  for each row execute function set_updated_at();

-- RLS: public read, service-role write only (matches every other table).
alter table artist_spotify_cache enable row level security;
drop policy if exists "Public read artist_spotify_cache" on artist_spotify_cache;
create policy "Public read artist_spotify_cache"
  on artist_spotify_cache for select using (true);

-- ── Rollback ────────────────────────────────────────────────
-- drop table if exists artist_spotify_cache cascade;
