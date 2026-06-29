# v4 Ralph Loop — State

Tracks per-area progress so each iteration resumes cleanly. Order is locked in PLAN.md.

| # | Area | Branch | Status |
|---|------|--------|--------|
| 4 | Artist pipeline | `v4.1-artist-pipeline` | DONE (merged) |
| 7 | Festival data quality | `v4.2-festival-data` | DONE (merged) |
| 1 | Header light/dark | `v4.3-header-theme` | IN PROGRESS |
| 6 | Accessibility panel | `v4.4-a11y` | todo |
| 2 | Homepage | `v4.5-homepage` | todo |
| 3 | Festival page | `v4.6-festival-page` | todo |
| 5 | Footer | `v4.7-footer` | todo |
| 8 | Search | `v4.8-search` | todo |
| 9 | Wallpaper rebuild | `v4.9-wallpaper` | todo |

## #4 notes (diagnosis + fix)
- **Root cause:** Spotify 2026 API returns null popularity/followers/genres for our
  client-credentials token (verified even on Olivia Rodrigo, via /search AND /artists/{id}).
  Spotify gives only spotify_id + image. Plus sync had only run for 17/181 Lolla artists,
  and no source ever supplied bios.
- **Fix:** new `pipeline/artist_bio_enricher.py` — MusicBrainz (genres via tags +
  Wikipedia/Wikidata relation) + Wikipedia REST (bio) + Deezer (popularity proxy +
  followers + image). Writes existing `artists` columns (frontend reads them as the
  `withSpotifyCache` fallback — zero frontend change). Best-effort `artist_bio_cache`
  TTL ledger (migration `20260629_v4_1_artist_bio_cache.sql`).
- Added daily `enrich-bios` job to `etl_daily.yml`. Added `musicbrainzngs` to requirements.
- **Manual step pending:** apply `db/migrations/20260629_v4_1_artist_bio_cache.sql` in the
  Supabase SQL editor (no migration runner / DATABASE_URL available locally). Feature works
  without it; the table only persists the TTL freshness ledger.

## #7 notes (festival data quality)
- **Root cause:** `db/seed_sources.sql` was never applied to the live DB (only 3
  manual_config rows), so the v3 source-driven lineup ingestion had zero sources →
  daily lineup job was a no-op. And the dates enricher skipped any festival that
  already had a date, so 75/76 stayed on estimates forever.
- **Dates fix** (`festival_dates_enricher.py`): re-confirm estimated dates (don't
  skip), load TM keywords from `festival_targets.csv` (~110 vs 9 hardcoded), and a
  contiguous-substring name filter (`_tm_event_matches`) that rejects same-venue
  noise. Result: 1→11 festivals with real TM-confirmed 2026 dates; rest stay
  honestly estimated. Added `from __future__ import annotations` (the file's
  `X | None` annotations crashed on Python 3.9). Offline `--self-test`.
- **Lineups fix:** new `seed_lineup_sources.py` seeds `ticketmaster_lineup` sources
  from the CSV for festivals that exist in the DB. Ran `ingest_lineups.py` → real
  TM lineups: ACL +168 (Charli xcx, Skrillex, Lorde, Twenty One Pilots),
  Outside Lands +90 (Turnstile, The Strokes), Shaky Knees +53. Festivals not on TM
  got +0 → honest TBA (Gov Ball verified showing TBA live).
- **NON-destructive call:** 464 `source=None` lineup rows are a MIX — Coachella's
  20 are venue-noise (country acts), but Bonnaroo (97), Ohana, Newport Folk are
  REAL curated lineups. A blanket delete would destroy real data, so left as-is.
  Lolla stays `source='official'` (untouched).
- **Known follow-up (not a blocker):** per-festival cleanup of the noisy `source=None`
  rows (Coachella/EDC/Ultra) needs manual verification — can't be auto-cleaned
  safely and those lineups aren't on any free API. Featured/Wallpaper exclusion of
  no-real-lineup festivals is implemented in #2/#9 (they depend on this data).
- **Manual step pending:** none required for this to work live. (Optional: apply the
  full `db/seed_sources.sql` for the aggregator/metadata sources too.)

## #1 notes (header light/dark)
- Dark stays the brand default; `ThemeToggle.tsx` (client) persists `theme` to
  localStorage and flips `<html data-theme>`. No-flash inline script in `layout.tsx`
  sets it before paint; `<html suppressHydrationWarning>`. Body text → `var(--text)`.
- Full tuned light palette in `app/globals.css` under `[data-theme="light"]`. The app
  was dark-first with hardcoded `text-white`/`bg-black`/`border-white/*` across ~46
  files; rather than rewrite all of them, the neutral utilities are remapped to
  semantic tokens under the theme attribute via attribute selectors + `!important`
  (escaped-slash class selectors got mangled by PostCSS — attribute selectors avoid
  that). Hero-over-image text keeps white via an `.over-media` wrapper on FestivalHero
  + HeroSection.
- **Key fix:** `lib/festival-theme.ts` `themeToCssVars` used to inject hardcoded DARK
  `--surface/--text/--text-muted` on every FestivalThemeStyle subtree, pinning all
  festival/artist pages to dark. Now it injects ACCENT vars only; surface/text inherit
  the root theme so those pages flip too. Removed the now-dead palette fields.
- Verified live in Playwright: homepage + festival pages flip correctly in light, hero
  text stays white, dark mode unregressed.

## Env note
- Local pipeline venv: `pipeline/.venv` (Python 3.9, deps installed). Gitignored.
- Shell cwd resets to repo root after sandbox-disabled commands — always `cd pipeline` first.
