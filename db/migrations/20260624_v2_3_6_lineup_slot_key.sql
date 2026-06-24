-- Migration: 20260624_v2_3_6_lineup_slot_key  (v2.3.6)
-- Make lineups uniqueness represent a *set*, not just an appearance, so an
-- artist can play multiple sets (multi-day, multiple stages). The old key
-- (festival_id, artist_id, year) collapsed every such artist to one row,
-- silently dropping sets (10 of 191 for Lolla 2026). NULLS NOT DISTINCT (PG15+)
-- keeps scraped null-day/null-time rows idempotent (nulls treated as equal).
-- Additive/idempotent; run in the Supabase SQL editor.

alter table lineups drop constraint if exists lineups_festival_id_artist_id_year_key;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'lineups_slot_key') then
    alter table lineups
      add constraint lineups_slot_key
      unique nulls not distinct (festival_id, artist_id, year, day, set_time_start);
  end if;
end $$;

-- Conflict policy on the INSERT path: a non-verified source must not add a NEW
-- row for an artist/year a verified source already covers (the widened key would
-- otherwise let a scraper's null-time row sit next to the official timed row).
-- Pairs with protect_verified_lineups (the UPDATE path).
create or replace function skip_unverified_insert()
returns trigger as $$
begin
  if (new.source is null or new.source not in ('official', 'wikipedia'))
     and exists (
       select 1 from lineups l
       where l.festival_id = new.festival_id
         and l.artist_id = new.artist_id
         and l.year = new.year
         and l.source in ('official', 'wikipedia')
     ) then
    return null;  -- drop the scraped insert; the verified row stands
  end if;
  return new;
end;
$$ language plpgsql;

drop trigger if exists lineups_skip_unverified_insert on lineups;
create trigger lineups_skip_unverified_insert
  before insert on lineups
  for each row execute function skip_unverified_insert();

-- ── Rollback ────────────────────────────────────────────────
-- drop trigger if exists lineups_skip_unverified_insert on lineups;
-- drop function if exists skip_unverified_insert();
-- alter table lineups drop constraint if exists lineups_slot_key;
-- alter table lineups add constraint lineups_festival_id_artist_id_year_key
--   unique (festival_id, artist_id, year);
