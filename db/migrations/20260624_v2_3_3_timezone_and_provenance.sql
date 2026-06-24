-- Migration: 20260624_v2_3_3_timezone_and_provenance  (v2.3.3)
-- Timezone-correct schedule storage + lineup provenance/trust.
-- Additive + idempotent; safe to re-run. Run in the Supabase SQL editor.
--
-- Model: set times (lineups.set_time_*) stay LOCAL to the festival. A bare
-- `time` of 23:00 on 2026-08-01 only means something with the festival's zone,
-- so festivals.timezone (IANA) carries it. We deliberately do NOT convert to
-- UTC — an all-day local schedule converted to UTC corrupts the day boundary.

-- ── festivals.timezone (IANA, e.g. America/Chicago) ────────────
alter table festivals add column if not exists timezone text;

-- Backfill from state (one-shot, idempotent: only fills nulls). Default Eastern.
update festivals set timezone = case state
    when 'CA' then 'America/Los_Angeles'
    when 'NV' then 'America/Los_Angeles'
    when 'WA' then 'America/Los_Angeles'
    when 'OR' then 'America/Los_Angeles'
    when 'AZ' then 'America/Phoenix'
    when 'IL' then 'America/Chicago'
    when 'TX' then 'America/Chicago'
    when 'TN' then 'America/Chicago'
    when 'LA' then 'America/Chicago'
    when 'AL' then 'America/Chicago'
    when 'MN' then 'America/Chicago'
    when 'MO' then 'America/Chicago'
    when 'WI' then 'America/Chicago'
    when 'CO' then 'America/Denver'
    when 'NM' then 'America/Denver'
    when 'UT' then 'America/Denver'
    when 'MI' then 'America/Detroit'
    else 'America/New_York'
  end
  where timezone is null and state is not null;

-- ── lineups.source — provenance / trust ────────────────────────
-- official | wikipedia | ticketmaster | songkick | setlistfm | ocr | estimated
-- A row is "verified" iff source in ('official','wikipedia'); the UI flags the rest.
alter table lineups add column if not exists source text;

-- Lollapalooza is seeded from the hand-curated official poster
-- (lolla_schedule_seeder.py) — mark its existing rows verified.
update lineups l set source = 'official'
  from festivals f
  where l.festival_id = f.id and f.slug = 'lollapalooza' and l.source is null;

-- ── Conflict policy, enforced in the DB (not per-scraper) ──────
-- A lower-trust writer (any scraper) must never clobber a verified row. The
-- upsert's ON CONFLICT DO UPDATE fires this trigger; returning OLD makes that
-- update a no-op for verified rows. One rule here beats a guard in every writer.
-- (Note: official vs wikipedia are both "verified" — either may refresh the
-- other; refine the inter-verified ordering later if it ever matters.)
create or replace function protect_verified_lineups()
returns trigger as $$
begin
  if old.source in ('official', 'wikipedia')
     and (new.source is null or new.source not in ('official', 'wikipedia')) then
    return old;  -- keep the verified row intact
  end if;
  return new;
end;
$$ language plpgsql;

drop trigger if exists lineups_protect_verified on lineups;
create trigger lineups_protect_verified
  before update on lineups
  for each row execute function protect_verified_lineups();

-- ── Rollback ────────────────────────────────────────────────
-- drop trigger if exists lineups_protect_verified on lineups;
-- drop function if exists protect_verified_lineups();
-- alter table lineups   drop column if exists source;
-- alter table festivals drop column if exists timezone;
