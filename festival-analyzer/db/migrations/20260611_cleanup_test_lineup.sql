-- Wipe ALL Lollapalooza 2026 lineup entries (removes every test/seed artist).
-- After running this, re-seed the canonical schedule with:
--   python pipeline/lolla_schedule_seeder.py  (no guard now — table is empty)
-- Run in Supabase SQL editor.

DELETE FROM lineups
WHERE festival_id = (SELECT id FROM festivals WHERE slug = 'lollapalooza')
  AND year = 2026;

-- Mark Lollapalooza 2026 dates as confirmed (not estimated)
UPDATE festivals
SET dates_estimated = false
WHERE slug = 'lollapalooza';
