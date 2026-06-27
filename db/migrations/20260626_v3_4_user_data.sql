-- 20260626_v3_4_user_data.sql — v3.4 accounts + user-data backend (+ v3.8 prefs)
-- The home for favourites/playlists that were device-local IndexedDB (v2.7), plus
-- notification preferences (v3.8). Owner-scoped RLS (auth.uid() = user_id) — unlike
-- the public-read content tables, these are private per user. Additive + reversible.
-- NOTE: requires Supabase Auth enabled (auth.users present) — see the scaffold doc.

create table if not exists user_favorites (
  user_id    uuid not null references auth.users(id) on delete cascade,
  artist_id  uuid not null references artists(id) on delete cascade,
  created_at timestamptz default now(),
  primary key (user_id, artist_id)
);

create table if not exists user_playlists (
  id          uuid primary key default uuid_generate_v4(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  name        text not null,
  festival_id uuid references festivals(id) on delete set null,
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

create table if not exists user_playlist_items (
  playlist_id uuid not null references user_playlists(id) on delete cascade,
  artist_id   uuid not null references artists(id) on delete cascade,
  position    int default 0,
  primary key (playlist_id, artist_id)
);

create table if not exists notification_prefs (
  user_id             uuid primary key references auth.users(id) on delete cascade,
  lineup_changes      boolean default true,   -- favourite artist added/dropped
  set_time_reminders  boolean default true,
  channel             text default 'web_push' check (channel in ('web_push', 'email')),
  web_push_subscription jsonb,
  email               text,
  updated_at          timestamptz default now()
);

-- ── RLS: each user sees/writes only their own rows ─────────────
alter table user_favorites      enable row level security;
alter table user_playlists      enable row level security;
alter table user_playlist_items enable row level security;
alter table notification_prefs  enable row level security;

drop policy if exists "own favorites" on user_favorites;
create policy "own favorites" on user_favorites
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "own playlists" on user_playlists;
create policy "own playlists" on user_playlists
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Items inherit ownership from their playlist.
drop policy if exists "own playlist items" on user_playlist_items;
create policy "own playlist items" on user_playlist_items
  using (exists (select 1 from user_playlists p
                 where p.id = playlist_id and p.user_id = auth.uid()))
  with check (exists (select 1 from user_playlists p
                      where p.id = playlist_id and p.user_id = auth.uid()));

drop policy if exists "own notification prefs" on notification_prefs;
create policy "own notification prefs" on notification_prefs
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ── Rollback ───────────────────────────────────────────────────
-- drop table if exists user_playlist_items, user_playlists, user_favorites, notification_prefs;
