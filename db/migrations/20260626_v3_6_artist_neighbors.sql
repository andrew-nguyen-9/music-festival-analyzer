-- 20260626_v3_6_artist_neighbors.sql — v3.6 recommendations engine
-- Precomputed artist similarity (nightly via pipeline/recommend.py). Heuristic
-- score = genre overlap (Jaccard) + co-lineup graph (artists sharing a bill) +
-- a popularity prior. Additive + reversible (rollback drops the table).
-- RLS: public read (it's derived public data); writes are service-role only.

create table if not exists artist_neighbors (
  artist_id    uuid not null references artists(id) on delete cascade,
  neighbor_id  uuid not null references artists(id) on delete cascade,
  score        double precision not null,
  reason       text,            -- 'genre' | 'co-lineup' | 'blend'
  computed_at  timestamptz default now(),
  primary key (artist_id, neighbor_id),
  check (artist_id <> neighbor_id)
);

-- Hot path: "neighbors of artist X, best first".
create index if not exists idx_artist_neighbors_lookup
  on artist_neighbors (artist_id, score desc);

alter table artist_neighbors enable row level security;
drop policy if exists "artist_neighbors public read" on artist_neighbors;
create policy "artist_neighbors public read" on artist_neighbors for select using (true);

-- ── Rollback ───────────────────────────────────────────────────
-- drop table if exists artist_neighbors;
