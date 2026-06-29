-- ============================================================
-- Soundcheck — ONE-SHOT Supabase setup
-- Paste this entire file into the Supabase SQL editor and Run.
-- = schema.sql + seed_lolla.sql (runnable lineup section).
-- Idempotent: safe to re-run.
--
-- ⚠️  LEGACY / SUPERSEDED (v2.3). This bootstrap predates v2.1–v2.3 and is now
-- stale: it lacks artist_spotify_cache, the v2.1 indexes, festivals timezone /
-- lat-lng, lineups.source, the stages table, and still uses the OLD coarse
-- lineups key `(festival_id, artist_id, year)` that drops multi-set artists.
-- Do NOT bootstrap a new DB from this file. Canonical = `schema.sql` then the
-- timestamped files in `migrations/` (see db/README.md).
-- ============================================================

-- ============================================================
-- Soundcheck — Supabase Schema
-- Run this in the Supabase SQL editor to initialize the DB
-- ============================================================

-- Enable extensions
create extension if not exists "pg_trgm";      -- full-text fuzzy search
create extension if not exists "unaccent";      -- normalize accented artist names
create extension if not exists "uuid-ossp";    -- uuid generation

-- ============================================================
-- FESTIVALS
-- ============================================================
create table if not exists festivals (
  id            uuid primary key default uuid_generate_v4(),
  slug          text unique not null,              -- lollapalooza-chicago
  name          text not null,                     -- Lollapalooza
  city          text,
  state         text,
  country       text default 'US',
  venue         text,
  start_date    date,
  end_date      date,
  website_url   text,
  wikipedia_url text,
  description   text,
  tags          text[] default '{}',               -- ['rock', 'multi-genre', 'outdoor', 'annual']
  instagram_handle text,
  x_handle      text,
  accent_color  text,                              -- hex for festival theming, e.g. '#FF4500'
  hero_image_url text,
  logo_url      text,
  is_active     boolean default true,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

-- ============================================================
-- ARTISTS
-- ============================================================
create table if not exists artists (
  id              uuid primary key default uuid_generate_v4(),
  slug            text unique not null,
  name            text not null,
  bio             text,
  genres          text[] default '{}',
  origin_city     text,
  origin_country  text,
  website_url     text,
  spotify_id      text unique,
  apple_music_id  text,
  spotify_url     text,
  apple_music_url text,
  spotify_followers bigint,
  spotify_popularity int,                          -- 0–100
  preview_url     text,                            -- 30s Spotify preview
  image_url       text,
  header_image_url text,
  tags            text[] default '{}',
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

-- ============================================================
-- LINEUPS (festival × artist join)
-- ============================================================
create table if not exists lineups (
  id            uuid primary key default uuid_generate_v4(),
  festival_id   uuid references festivals(id) on delete cascade,
  artist_id     uuid references artists(id) on delete cascade,
  year          int not null,
  stage         text,                              -- Main Stage, Perry's, etc.
  day           date,
  set_time_start time,
  set_time_end   time,
  is_headliner  boolean default false,
  created_at    timestamptz default now(),
  unique (festival_id, artist_id, year)
);

-- ============================================================
-- MEDIA (photos per festival, sourced from Unsplash)
-- ============================================================
create table if not exists media (
  id              uuid primary key default uuid_generate_v4(),
  festival_id     uuid references festivals(id) on delete cascade,
  unsplash_id     text,
  url_regular     text,
  url_thumb       text,
  url_full        text,
  alt_text        text,
  photographer    text,
  photographer_url text,
  credit_html     text,                            -- required Unsplash attribution
  created_at      timestamptz default now()
);

-- ============================================================
-- SOCIAL POSTS (synced from IG + X per festival)
-- ============================================================
create table if not exists social_posts (
  id              uuid primary key default uuid_generate_v4(),
  festival_id     uuid references festivals(id) on delete cascade,
  platform        text not null check (platform in ('instagram', 'x')),
  post_id         text not null,
  post_url        text,
  content         text,
  media_url       text,
  media_type      text,                            -- image, video, carousel
  posted_at       timestamptz,
  like_count      int,
  comment_count   int,
  synced_at       timestamptz default now(),
  unique (platform, post_id)
);

-- ============================================================
-- FUN FACTS (AI-generated per festival × year)
-- ============================================================
create table if not exists fun_facts (
  id              uuid primary key default uuid_generate_v4(),
  festival_id     uuid references festivals(id) on delete cascade,
  year            int not null,
  facts           jsonb not null,                  -- array of {fact: string, category: string}
  generated_at    timestamptz default now(),
  model_version   text,
  unique (festival_id, year)
);

-- ============================================================
-- TAGS (normalized tag registry for filtering)
-- ============================================================
create table if not exists tags (
  id    uuid primary key default uuid_generate_v4(),
  slug  text unique not null,
  label text not null,
  type  text check (type in ('genre', 'vibe', 'format', 'region', 'season'))
);

-- Seed core tags
insert into tags (slug, label, type) values
  ('multi-genre', 'Multi-Genre', 'genre'),
  ('electronic', 'Electronic', 'genre'),
  ('hip-hop', 'Hip-Hop', 'genre'),
  ('rock', 'Rock', 'genre'),
  ('indie', 'Indie', 'genre'),
  ('edm', 'EDM', 'genre'),
  ('country', 'Country', 'genre'),
  ('jazz', 'Jazz', 'genre'),
  ('outdoor', 'Outdoor', 'format'),
  ('camping', 'Camping', 'format'),
  ('urban', 'Urban', 'format'),
  ('multi-day', 'Multi-Day', 'format'),
  ('annual', 'Annual', 'vibe'),
  ('flagship', 'Flagship', 'vibe'),
  ('midwest', 'Midwest', 'region'),
  ('southwest', 'Southwest', 'region'),
  ('southeast', 'Southeast', 'region'),
  ('west-coast', 'West Coast', 'region'),
  ('northeast', 'Northeast', 'region'),
  ('spring', 'Spring', 'season'),
  ('summer', 'Summer', 'season'),
  ('fall', 'Fall', 'season')
on conflict (slug) do nothing;

-- ============================================================
-- INDEXES
-- ============================================================

-- Fuzzy search on festival + artist names
create index if not exists idx_festivals_name_trgm on festivals using gin (name gin_trgm_ops);
create index if not exists idx_artists_name_trgm   on artists  using gin (name gin_trgm_ops);

-- Tag array search
create index if not exists idx_festivals_tags on festivals using gin (tags);
create index if not exists idx_artists_tags   on artists  using gin (tags);
create index if not exists idx_artists_genres on artists  using gin (genres);

-- Lineup lookups
create index if not exists idx_lineups_festival on lineups (festival_id, year);
create index if not exists idx_lineups_artist   on lineups (artist_id);

-- Social posts by festival + platform
create index if not exists idx_social_festival_platform on social_posts (festival_id, platform, posted_at desc);

-- ============================================================
-- FULL-TEXT SEARCH FUNCTION
-- Supports searching by festival name, city, tag, genre, artist name
-- ============================================================
create or replace function search_all(query text)
returns table (
  type        text,
  id          uuid,
  slug        text,
  name        text,
  description text,
  score       float
) as $$
  select
    'festival'::text as type,
    f.id, f.slug, f.name,
    f.description,
    similarity(f.name, query) as score
  from festivals f
  where f.name % query or f.tags @> array[lower(query)]
  union all
  select
    'artist'::text,
    a.id, a.slug, a.name,
    a.bio,
    similarity(a.name, query) as score
  from artists a
  where a.name % query or a.genres @> array[lower(query)]
  order by score desc
  limit 20;
$$ language sql stable;

-- ============================================================
-- ROW LEVEL SECURITY (public read, service role write)
-- ============================================================
alter table festivals    enable row level security;
alter table artists      enable row level security;
alter table lineups      enable row level security;
alter table media        enable row level security;
alter table social_posts enable row level security;
alter table fun_facts    enable row level security;
alter table tags         enable row level security;

-- Public read policies
create policy "Public read festivals"    on festivals    for select using (true);
create policy "Public read artists"      on artists      for select using (true);
create policy "Public read lineups"      on lineups      for select using (true);
create policy "Public read media"        on media        for select using (true);
create policy "Public read social_posts" on social_posts for select using (true);
create policy "Public read fun_facts"    on fun_facts    for select using (true);
create policy "Public read tags"         on tags         for select using (true);

-- ============================================================
-- UPDATED_AT triggers
-- ============================================================
create or replace function set_updated_at()
returns trigger as $$
begin new.updated_at = now(); return new; end;
$$ language plpgsql;

create trigger festivals_updated_at before update on festivals
  for each row execute function set_updated_at();

create trigger artists_updated_at before update on artists
  for each row execute function set_updated_at();


-- Lollapalooza 2026 seed data
-- Run after schema.sql to bootstrap Phase 1

-- Insert Lollapalooza
insert into festivals (
  slug, name, city, state, venue,
  start_date, end_date,
  website_url, wikipedia_url,
  description,
  instagram_handle, x_handle,
  accent_color, hero_image_url, tags
) values (
  'lollapalooza',
  'Lollapalooza',
  'Chicago', 'IL',
  'Grant Park',
  '2026-07-30', '2026-08-02',
  'https://www.lollapalooza.com',
  'https://en.wikipedia.org/wiki/Lollapalooza',
  'One of the longest-running and most iconic American music festivals, held annually in Grant Park in Chicago. Known for its diverse multi-genre lineup spanning rock, electronic, hip-hop, indie, and everything in between.',
  'lollapalooza', 'lollapalooza',
  '#FF4500',
  -- City image (Chicago skyline) used as the festival hero background
  'https://images.unsplash.com/photo-1631548637245-043803a8b776?q=80&w=987&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D',
  ARRAY['multi-genre', 'outdoor', 'annual', 'flagship', 'urban', 'summer', 'midwest']
)
on conflict (slug) do update set
  updated_at = now(),
  description = excluded.description,
  hero_image_url = excluded.hero_image_url,
  tags = excluded.tags;

-- Example artist inserts (replace with actual 2026 lineup when announced)
-- These will be enriched with Spotify data by artist_enricher.py
insert into artists (slug, name) values
  ('hozier', 'Hozier'),
  ('chappell-roan', 'Chappell Roan'),
  ('sabrina-carpenter', 'Sabrina Carpenter'),
  ('tyler-the-creator', 'Tyler, the Creator'),
  ('the-1975', 'The 1975'),
  ('charli-xcx', 'Charli xcx'),
  ('gracie-abrams', 'Gracie Abrams'),
  ('beabadoobee', 'beabadoobee'),
  ('interpol', 'Interpol'),
  ('lcd-soundsystem', 'LCD Soundsystem')
on conflict (slug) do nothing;

-- Connect artists to Lollapalooza 2026 lineup
-- (festival_id will need to be set to actual UUID after festival insert)
-- Run this after verifying the festival_id:
-- select id from festivals where slug = 'lollapalooza';

-- Template (replace {festival_id} with actual UUID):
/*
insert into lineups (festival_id, artist_id, year, is_headliner, stage) values
  ('{festival_id}', (select id from artists where slug = 'hozier'), 2026, true, 'Bud Light Stage'),
  ('{festival_id}', (select id from artists where slug = 'chappell-roan'), 2026, true, 'T-Mobile Stage'),
  ('{festival_id}', (select id from artists where slug = 'sabrina-carpenter'), 2026, true, 'Bud Light Stage'),
  ('{festival_id}', (select id from artists where slug = 'tyler-the-creator'), 2026, true, 'T-Mobile Stage'),
  ('{festival_id}', (select id from artists where slug = 'the-1975'), 2026, false, 'Perry''s'),
  ('{festival_id}', (select id from artists where slug = 'charli-xcx'), 2026, false, 'Bud Light Stage'),
  ('{festival_id}', (select id from artists where slug = 'gracie-abrams'), 2026, false, 'BMI Stage'),
  ('{festival_id}', (select id from artists where slug = 'beabadoobee'), 2026, false, 'BMI Stage'),
  ('{festival_id}', (select id from artists where slug = 'interpol'), 2026, false, 'T-Mobile Stage'),
  ('{festival_id}', (select id from artists where slug = 'lcd-soundsystem'), 2026, false, 'Perry''s')
on conflict (festival_id, artist_id, year) do nothing;
*/

-- ============================================================
-- RUNNABLE lineup seed (no manual UUID needed)
-- Resolves festival_id + artist_id via subquery, so this whole file
-- can be pasted into the Supabase SQL editor and run in one shot,
-- after schema.sql. Idempotent (safe to re-run).
-- ============================================================
insert into lineups (festival_id, artist_id, year, is_headliner, stage, day) values
  ((select id from festivals where slug = 'lollapalooza'), (select id from artists where slug = 'hozier'),            2026, true,  'Bud Light Stage', '2026-07-30'),
  ((select id from festivals where slug = 'lollapalooza'), (select id from artists where slug = 'chappell-roan'),     2026, true,  'T-Mobile Stage',  '2026-07-30'),
  ((select id from festivals where slug = 'lollapalooza'), (select id from artists where slug = 'sabrina-carpenter'), 2026, true,  'Bud Light Stage', '2026-07-31'),
  ((select id from festivals where slug = 'lollapalooza'), (select id from artists where slug = 'tyler-the-creator'), 2026, true,  'T-Mobile Stage',  '2026-07-31'),
  ((select id from festivals where slug = 'lollapalooza'), (select id from artists where slug = 'the-1975'),          2026, false, 'Perry''s',         '2026-08-01'),
  ((select id from festivals where slug = 'lollapalooza'), (select id from artists where slug = 'charli-xcx'),        2026, false, 'Bud Light Stage', '2026-08-01'),
  ((select id from festivals where slug = 'lollapalooza'), (select id from artists where slug = 'gracie-abrams'),     2026, false, 'BMI Stage',       '2026-08-01'),
  ((select id from festivals where slug = 'lollapalooza'), (select id from artists where slug = 'beabadoobee'),       2026, false, 'BMI Stage',       '2026-08-02'),
  ((select id from festivals where slug = 'lollapalooza'), (select id from artists where slug = 'interpol'),          2026, false, 'T-Mobile Stage',  '2026-08-02'),
  ((select id from festivals where slug = 'lollapalooza'), (select id from artists where slug = 'lcd-soundsystem'),   2026, false, 'Perry''s',         '2026-08-02')
on conflict (festival_id, artist_id, year) do nothing;

-- Sanity check (optional): how many artists are linked?
-- select f.name, count(*) as artists
-- from lineups l join festivals f on f.id = l.festival_id
-- where f.slug = 'lollapalooza' and l.year = 2026
-- group by f.name;
