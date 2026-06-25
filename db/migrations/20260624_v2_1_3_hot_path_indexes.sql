-- Migration: 20260624_v2_1_3_hot_path_indexes  (v2.1.3)
-- Add indexes for hot query paths. Additive + idempotent; safe to re-run.
-- Run in the Supabase SQL editor.
--
-- Already covered (no index added — would be redundant):
--   festivals.slug, artists.slug, artists.spotify_id  -> UNIQUE constraints (implicit btree)
--   lineup joins                                       -> idx_lineups_festival / idx_lineups_artist
--   fuzzy name search, tag/genre filters               -> existing GIN indexes

-- Home / featured listing: active festivals ordered by start_date.
create index if not exists idx_festivals_active_start
  on festivals (is_active, start_date);

-- Popularity sort (lineup-by-popularity, artist ranking).
create index if not exists idx_artists_popularity
  on artists (spotify_popularity desc nulls last);

-- ── Rollback ────────────────────────────────────────────────
-- drop index if exists idx_festivals_active_start;
-- drop index if exists idx_artists_popularity;
