# v4 Ralph Loop — State

Tracks per-area progress so each iteration resumes cleanly. Order is locked in PLAN.md.

| # | Area | Branch | Status |
|---|------|--------|--------|
| 4 | Artist pipeline | `v4.1-artist-pipeline` | DONE (merged) |
| 7 | Festival data quality | `v4.2-festival-data` | DONE (merged) |
| 1 | Header light/dark | `v4.3-header-theme` | DONE (merged) |
| 6 | Accessibility panel | `v4.4-a11y` | DONE (merged) |
| 2 | Homepage | `v4.5-homepage` | DONE (merged) |
| 3 | Festival page | `v4.6-festival-page` | DONE (merged) |
| 5 | Footer | `v4.7-footer` | DONE (merged) |
| 8 | Search | `v4.8-search` | DONE (merged) |
| 9 | Wallpaper rebuild | `v4.9-wallpaper` | DONE (merged) |

**All 9 areas complete + merged to `v4`.** Phase NOT closed — awaiting owner review before
the phase-close gates (full QA, ultra code-review, merge v4 → main). Do not PR to main
until approved.

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

## #6 notes (accessibility panel)
- `lib/settings.ts` central model; `SettingsPanel.tsx` gear popover in Nav. All
  persist to localStorage, apply via `<html>` classes. Pre-paint inline script in
  layout extended to apply them (no flash) — mirrors lib/settings.ts.
- High contrast (`hc`): extreme tokens per theme. Reduced motion (`rm`): CSS kills
  transitions/animations + `MotionProvider` forces Framer `reducedMotion="always"`.
  Color vision (`cb-protanopia|deuteranopia|tritanopia`): curated Okabe-Ito accents,
  NOT a filter — overrides FestivalThemeStyle's inline accent via the `.festival-theme`
  hook (stylesheet !important beats element inline normal). Font size (`fs-s|m|l|xl`):
  scales root font-size (rem-based UI).
- Footer shortcut wired: dispatch `soundcheck:open-a11y` to open the panel (#5).
- Verified live (Playwright): all 4 settings apply pre-paint; colorblind beats the
  festival accent (#e69f00 on ACL); XL = 20px root; HC surface = pure black.
- Pre-existing console noise (NOT from #6, possible later follow-ups): `/icon.svg` 500,
  `festival_guides` table missing.

## #2 notes (homepage)
- `FeaturedFestivals.tsx`: grid → horizontal scroll-snap carousel (`<ul>` + native
  overflow-x, `.no-scrollbar`, snap-x). Reduced-motion safe (no JS animation).
- `getFeaturedFestivals`: added `.eq("dates_estimated", false)` so only real-data
  (TM/official-confirmed) flagships qualify — keeps Coachella's noise + Gov Ball's
  emptiness out. Currently surfaces Lollapalooza + Outside Lands.
- `FestivalCard.tsx`: reading order now name → location → date → genre pills (was
  location → name → date). Also added the missing `.over-media` class so card text
  stays white over the image scrim in BOTH themes (a #1 gap — cards are over-media).
- Verified live (Playwright): carousel scrolls, order correct, card text white in
  light + dark.

## #3 notes (festival page)
- **Full removal:** deleted MediaGallery / SocialFeed / FunFactsWidget components,
  their queries (getMedia/getSocialPosts/getFunFacts) + media/social/funFacts from
  getFestivalPageData + FestivalPageData type, pipeline media_fetcher.py +
  fun_facts_generator.py, and the dead cron jobs (fetch-media, sync-social-feeds,
  generate-fun-facts). Kept DraggableNotes (used by not-found.tsx, not the festival
  page). Removed now-unused type imports.
- **LineupAnalysis expanded — all four:** (1) genre breakdown adds a Shannon-evenness
  diversity score + dominant-genre chips; (2) popularity & discovery adds a
  headliner/mainstream/rising mix bar (on top of existing tiers + hidden gems);
  (3) NEW schedule conflicts — overlapping must-see sets (headliner OR pop≥65) on
  different stages, per-day set density (verified on Lolla: 12 overlaps, 47–48
  sets/day); (4) NEW comparisons — vs past years + vs peer festivals (new
  getFestivalComparison query, threaded page→tabs→analysis as a prop).
- Verified live on Lollapalooza: all four sections render with real data; removed
  sections gone; no new console errors.

## #8 notes (search)
- Extended search in the query/route layer (PostgREST), NOT a new SQL RPC, because
  this env can't apply migrations. `searchEnhanced` merges four sources, de-duped by
  (type,id), highest score wins:
  1. trigram `search_all` RPC (existing typo tolerance);
  2. ILIKE substring names (fixes a real gap: "bonnaroo" / "gov ball" didn't match
     the longer official names via trigram);
  3. location — city/state exact match + radius "nearby" via haversine over festival
     lat/lng (Chicago → Chicago fests + "Electric Forest 129 mi away"); state-name →
     abbrev map;
  4. genre — artists by genres[] + festivals by tags[], with a synonym map
     (edm→electronic/house…, hip hop→rap/trap…).
- Wired into app/api/search/route.ts + app/search/page.tsx.
- ponytail: skipped bloom filters — Postgres trigram + GIN already give fuzzy
  matching at this catalog size; a bloom filter only avoids lookups we do cheaply.
- Verified live: location, radius, genre, synonyms, substring all return correct results.

## #9 notes (wallpaper rebuild)
- Full rewrite of `WallpaperStudio.tsx` from a day-schedule canvas to a curated
  artist-list wallpaper. Kept raw canvas (no html-to-image dep) for a true 1170×2532
  PNG export.
- Starts EMPTY (`useState(new Set())`); "+ Add all headliners" one-tap (is_headliner
  flag, falls back to top-popularity); Clear; 40-artist cap (checkboxes disable at max).
- Strict 3-zone geometry: top third = clock/widget negative space (+ accent glow);
  center = "MY LINEUP / {FESTIVAL}" header + vertically-centered, auto-scaling artist
  list (font shrinks with count + to fit width); bottom = Soundcheck wordmark
  (brand-gradient) + soundcheck.an9.dev, bottom-center in the safe zone. Killed the
  stale "festivalanalyzer" string.
- Filters: stage (if any) + genre dropdowns; sort popularity / alphabetical.
- Colors: Dark/Light/Accent/Mono presets + custom BG + Text color pickers.
- Desktop: controls left, sticky phone preview right (fits one screen). Mobile:
  full preview + pull-up bottom-sheet drawer for controls.
- **Bug found + fixed:** desktop + mobile previews initially shared one ref, so React
  only attached it to the hidden mobile canvas and the visible one stayed blank
  (transparent pixels). Split into two refs, draw to both.
- Dropped the now-unused `stages` prop + getStages from the wallpaper page (stages are
  derived from lineup entries).
- Verified live (Playwright): empty start, headliners populate, 3 zones render,
  branding present, Light palette swaps bg. Gate green.

## Env note
- Local pipeline venv: `pipeline/.venv` (Python 3.9, deps installed). Gitignored.
- Shell cwd resets to repo root after sandbox-disabled commands — always `cd pipeline` first.
