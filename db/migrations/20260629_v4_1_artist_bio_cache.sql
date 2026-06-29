-- Migration: 20260629_v4_1_artist_bio_cache  (v4.1)
-- External-data cache for artist bios + genre tags sourced from MusicBrainz /
-- Wikipedia (Spotify's 2026 API returns null bio/genres/popularity for our
-- client-credentials token). Mirrors artist_spotify_cache TTL semantics so the
-- enricher can refresh stale rows with `where expires_at < now()`.
--
-- The resolved bio/genres/popularity are ALSO mirrored into the artists table
-- (artists.bio / genres / spotify_popularity / image_url), which the frontend
-- already reads as the fallback under withSpotifyCache (`cache.X ?? artists.X`).
-- This cache table exists purely as the pipeline-side freshness ledger so reruns
-- are idempotent and don't re-hammer MusicBrainz/Wikipedia within the TTL.
-- Additive + idempotent; safe to re-run. Run in the Supabase SQL editor.

create table if not exists artist_bio_cache (
  id            uuid primary key default uuid_generate_v4(),
  artist_id     uuid not null unique references artists(id) on delete cascade,
  bio           text,
  source        text,                                 -- 'wikipedia' | 'none'
  source_url    text,                                 -- wikipedia/wikidata URL
  mbid          text,                                 -- MusicBrainz artist id
  genres        text[] default '{}',                  -- MusicBrainz tags
  fetched_at    timestamptz not null default now(),
  ttl_seconds   int not null default 2592000,         -- 30 days (bios change rarely)
  expires_at    timestamptz,                          -- = fetched_at + ttl_seconds (trigger)
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

create index if not exists idx_artist_bio_cache_expires
  on artist_bio_cache (expires_at);

-- Reuse the same expiry maintenance the spotify cache uses (set_artist_cache_expiry
-- maintains expires_at + updated_at on insert/update).
drop trigger if exists artist_bio_cache_expiry on artist_bio_cache;
create trigger artist_bio_cache_expiry
  before insert or update on artist_bio_cache
  for each row execute function set_artist_cache_expiry();

-- RLS: public read, service-role write only (matches every other table).
alter table artist_bio_cache enable row level security;
drop policy if exists "Public read artist_bio_cache" on artist_bio_cache;
create policy "Public read artist_bio_cache"
  on artist_bio_cache for select using (true);

-- ── Rollback ────────────────────────────────────────────────
-- drop table if exists artist_bio_cache cascade;
