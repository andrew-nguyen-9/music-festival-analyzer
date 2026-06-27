-- 20260626_v3_3_search_ranking.sql — v3.3 search at scale
-- Upgrade search_all from pure name-similarity to weighted ranking (popularity +
-- recency + city/tag/genre match), and add search_suggest for "did you mean?".
-- Additive + reversible: both are `create or replace function` — the rollback block
-- at the bottom restores the v2 similarity-only definition. Trigram GIN indexes
-- (idx_festivals_name_trgm / idx_artists_name_trgm) already exist from schema.sql.

create or replace function search_all(query text)
returns table (
  type        text,
  id          uuid,
  slug        text,
  name        text,
  description text,
  score       float
) as $$
  -- Festivals: best of name/city trigram similarity, boosted for upcoming editions.
  select 'festival'::text as type, f.id, f.slug, f.name, f.description,
         greatest(similarity(f.name, query), similarity(coalesce(f.city, ''), query))
           * (case when f.start_date >= current_date then 1.25
                   when f.start_date is null then 1.0
                   else 0.85 end) as score
  from festivals f
  where (f.name % query or f.city % query or f.tags @> array[lower(query)])
    and f.is_active
  union all
  -- Artists: name similarity, boosted by Spotify popularity (0–100 → 0.8–1.2x).
  select 'artist'::text, a.id, a.slug, a.name, a.bio,
         similarity(a.name, query)
           * (0.8 + 0.4 * coalesce(a.spotify_popularity, 0) / 100.0) as score
  from artists a
  where a.name % query or a.genres @> array[lower(query)]
  order by score desc
  limit 25;
$$ language sql stable;

-- "Did you mean?" — closest few names ignoring the % threshold, for zero-result UX.
create or replace function search_suggest(query text)
returns table (type text, slug text, name text, score float) as $$
  select 'festival'::text, f.slug, f.name, similarity(f.name, query) as score
  from festivals f where f.is_active
  union all
  select 'artist'::text, a.slug, a.name, similarity(a.name, query)
  from artists a
  order by score desc
  limit 3;
$$ language sql stable;

-- ── Rollback ───────────────────────────────────────────────────
-- drop function if exists search_suggest(text);
-- create or replace function search_all(query text)
-- returns table (type text, id uuid, slug text, name text, description text, score float) as $$
--   select 'festival'::text, f.id, f.slug, f.name, f.description, similarity(f.name, query)
--   from festivals f where f.name % query or f.tags @> array[lower(query)]
--   union all
--   select 'artist'::text, a.id, a.slug, a.name, a.bio, similarity(a.name, query)
--   from artists a where a.name % query or a.genres @> array[lower(query)]
--   order by score desc limit 20;
-- $$ language sql stable;
