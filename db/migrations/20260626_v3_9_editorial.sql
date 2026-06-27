-- 20260626_v3_9_editorial.sql — v3.9 editorial content model
-- Festival guides + artist spotlights (authored, optionally Claude-assisted).
-- Public read ONLY when published (published_at is not null) — drafts stay private.
-- Additive + reversible. Body is markdown; the UI renders it as paragraphs.

create table if not exists festival_guides (
  id           uuid primary key default uuid_generate_v4(),
  festival_id  uuid not null references festivals(id) on delete cascade,
  slug         text not null,
  title        text not null,
  body_md      text not null,
  author       text,
  published_at timestamptz,
  created_at   timestamptz default now(),
  updated_at   timestamptz default now(),
  unique (festival_id, slug)
);

create table if not exists artist_spotlights (
  id           uuid primary key default uuid_generate_v4(),
  artist_id    uuid not null references artists(id) on delete cascade,
  slug         text not null,
  title        text not null,
  body_md      text not null,
  author       text,
  published_at timestamptz,
  created_at   timestamptz default now(),
  unique (artist_id, slug)
);

create index if not exists idx_festival_guides_festival on festival_guides (festival_id);
create index if not exists idx_artist_spotlights_artist on artist_spotlights (artist_id);

alter table festival_guides   enable row level security;
alter table artist_spotlights enable row level security;

drop policy if exists "published guides public read" on festival_guides;
create policy "published guides public read" on festival_guides
  for select using (published_at is not null);

drop policy if exists "published spotlights public read" on artist_spotlights;
create policy "published spotlights public read" on artist_spotlights
  for select using (published_at is not null);

-- ── Rollback ───────────────────────────────────────────────────
-- drop table if exists festival_guides, artist_spotlights;
