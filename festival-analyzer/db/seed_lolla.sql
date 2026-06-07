-- Lollapalooza 2026 seed data
-- Run after schema.sql to bootstrap Phase 1

-- Insert Lollapalooza
insert into festivals (
  slug, name, city, state, venue,
  start_date, end_date,
  website_url, wikipedia_url,
  description,
  instagram_handle, x_handle,
  accent_color, tags
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
  ARRAY['multi-genre', 'outdoor', 'annual', 'flagship', 'urban', 'summer', 'midwest']
)
on conflict (slug) do update set
  updated_at = now(),
  description = excluded.description,
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
