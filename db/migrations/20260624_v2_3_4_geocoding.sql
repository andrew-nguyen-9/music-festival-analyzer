-- Migration: 20260624_v2_3_4_geocoding  (v2.3.4)
-- Geocoded festival coordinates + per-stage coordinates for v2.8 (phone bg).
-- Additive + idempotent; safe to re-run. Run in the Supabase SQL editor.

-- ── festivals: venue-level coordinates (Nominatim) ─────────────
-- latitude/longitude + geocoded_at double as the geocode CACHE: the enricher
-- skips any festival already geocoded, so the daily cron never re-hits the API.
alter table festivals add column if not exists latitude    double precision;
alter table festivals add column if not exists longitude   double precision;
alter table festivals add column if not exists geocoded_at timestamptz;

-- ── stages: per-festival stage coordinates ─────────────────────
-- Keyed unique on (festival_id, name). v2.8 joins lineups.stage = stages.name.
-- coords_source: 'known' (seeded from published layout) | 'venue_centroid'
-- (festival lat/lng spread, when no per-stage layout is available).
create table if not exists stages (
  id            uuid primary key default uuid_generate_v4(),
  festival_id   uuid not null references festivals(id) on delete cascade,
  name          text not null,
  latitude      double precision,
  longitude     double precision,
  coords_source text,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now(),
  unique (festival_id, name)
);

create index if not exists idx_stages_festival on stages (festival_id);

create trigger stages_updated_at before update on stages
  for each row execute function set_updated_at();

-- RLS: public read, service-role write (new tables require this — CLAUDE.md).
alter table stages enable row level security;
create policy "Public read stages" on stages for select using (true);

-- ── Rollback ────────────────────────────────────────────────
-- drop table if exists stages;
-- alter table festivals drop column if exists geocoded_at;
-- alter table festivals drop column if exists longitude;
-- alter table festivals drop column if exists latitude;
