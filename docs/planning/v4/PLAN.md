# v4 — UX, Accessibility, Pipeline & Wallpaper Overhaul

> Phase **v4**. Cut `v4` branch off `main`; segment sub-branches per area
> (`v4.1-*`, `v4.2-*`, …); task = commit. Never commit to `main`. Each segment
> gate: `next build` + `tsc --noEmit` + `next lint` green → commit → merge to
> `v4` → delete sub-branch. Full rules: [`docs/WORKFLOW.md`](../../WORKFLOW.md).

This plan is the source of truth for a large multi-area request. All decisions
below were locked with the product owner. Execute **pipeline/data first**, then
UI. One area per Ralph loop iteration.

## Global decisions (apply everywhere)

- **Settings storage:** `localStorage` only (no auth, no DB). Read on client;
  guard against SSR. Accept no cross-device sync.
- **Dependencies:** allow vetted, well-maintained libs only when they clearly
  beat hand-rolling (e.g. `html-to-image` for wallpaper export, a MusicBrainz
  client). Prefer stdlib/native first. Justify each new dep in its commit.
- **Per-area gate:** `next build` && `tsc --noEmit` && `next lint` must pass
  before commit. Pipeline areas additionally run the script end-to-end against
  the real Supabase + APIs (creds are in `pipeline/.env` and repo secrets).
- **Theme:** dark is the brand default. A header toggle opts into a **full,
  properly-tuned light theme** (redo CSS variables across all components, not a
  cheap invert). Theme persists in localStorage.
- **No regressions:** respect existing `prefers-reduced-motion`, RLS, anon-key
  rules, and "no client-side Spotify" constraints in CLAUDE.md.

---

## Run order

1. **#4 Artist enrichment pipeline** (data — unblocks artist pages)
2. **#7 Festival dates/lineups data quality** (data — unblocks homepage/cards/wallpaper)
3. **#1 Header light/dark**
4. **#6 Accessibility settings panel**
5. **#2 Homepage** (featured carousel + card label reorder)
6. **#3 Festival page** (remove sections + expand lineup analysis)
7. **#5 Footer**
8. **#8 Search** (location + genre + ranking)
9. **#9 Make-your-wallpaper rebuild**

---

## #4 — Artist pipeline (acceptance: Lollapalooza 2026 fully enriched)

Frontend is correct: `app/artist/[slug]/page.tsx` reads `artist_spotify_cache`
via `getArtistSpotifyCache` + `withSpotifyCache`, and falls back to a "thin
data" `EmptyState`. The break is **upstream** in the pipeline.

**Tasks:**
1. **Diagnose first.** Run `python spotify_sync.py --festival lollapalooza --year 2026`
   and `python artist_enricher.py` locally with `rich` logs. Determine the real
   cause (creds, cron not running, `MATCH_THRESHOLD=0.85` too strict so no
   matches, or write failures). Do not assume — fix the actual root cause.
2. **Bios from an external source.** Spotify provides no bio. Wire bios from
   MusicBrainz / Wikipedia / Last.fm (pick the most reliable free one; vetted
   client lib OK). Cache bio with `fetched_at` + TTL like other external data.
   Use `tenacity` retries, idempotent upsert.
3. **Stats + music:** ensure `spotify_popularity`, `genres`, `spotify_id` land
   in `artist_spotify_cache`. Keep the **auth-free Spotify embed** for playback
   (preview URLs stay null per 2026 API — do not chase them).
4. **Verify live:** every Lolla 2026 artist page shows bio + stats + playable
   embed. Confirm by loading real pages (not just script exit code). Fix the
   GitHub Actions cron (`etl_daily.yml`) if it was the cause.

## #7 — Festival data quality (acceptance: top ~20–30 US festivals accurate)

Lineup APIs already wired in `pipeline/.env`: Ticketmaster Discovery (primary),
SeatGeek (cross-validation), Setlist.fm (historical fallback).

**Tasks:**
1. Improve scrapers/enrichers (`festival_scraper.py`,
   `festival_dates_enricher.py`, `lineup_scraper.py`, `aggregator.py`) to pull
   **real dates + lineups** for the top ~20–30 US festivals (Coachella, Lolla,
   Bonnaroo, ACL, EDC, Gov Ball, Outside Lands, etc.) from authoritative sources.
2. **Mix pragmatic acquisition:** prefer official APIs (Ticketmaster/SeatGeek/
   Bandsintown/Songkick) where free/easy; HTML-scrape the rest with caching +
   `tenacity`. Respect robots/ToS.
3. **Verification:** only set `dates_estimated`/TBD when data is genuinely
   unknown. Festivals with no real lineup **show with an honest "lineup TBA"**
   (keep `FestivalTBD`), but are excluded from Featured and Wallpaper.
4. Keep idempotent upserts; re-runnable safely.

## #1 — Header light/dark

- Add a toggle in `components/Nav.tsx` (dark default → light). Persist to
  localStorage; apply via a `data-theme`/class on `<html>` set before paint to
  avoid flash (small inline script in `app/layout.tsx` is acceptable).
- Build a **full light palette** in `app/globals.css` CSS variables; audit every
  component for hardcoded `text-white`/`bg-*` that breaks in light mode.
- Re-check festival-accent contrast against light surfaces.

## #6 — Accessibility (settings panel/menu)

One accessibility panel (gear/menu in header; also add a footer shortcut to open
it — see #5). All toggles persist to localStorage and apply via `<html>` classes
+ CSS variables:

- **High contrast:** dedicated high-contrast token set.
- **Reduced motion:** force-disable Framer Motion / transitions; complements the
  existing `prefers-reduced-motion` handling (manual override).
- **Color-blind:** **curated safe palettes** (protanopia / deuteranopia /
  tritanopia) that swap festival accents for distinguishable colors. Not a CSS
  filter.
- **Font sizes:** multiple steps (e.g. S / M / L / XL) scaling a root `rem`
  base; verify layouts don't break at XL.

## #2 — Homepage

- **Featured = carousel.** Keep curation logic but render featured festivals in a
  scrollable carousel (`components/FeaturedFestivals.tsx`). Only festivals with
  real data qualify (depends on #7). Reduced-motion safe.
- **Card label reorder** (`components/FestivalCard.tsx`): reading order becomes
  **name → location → date → genre pills** (currently location → name → date →
  pills). Name stays the visual anchor; reorder source/markup to match.

## #3 — Festival page

- **Full removal** of gallery, social, "did you know?": delete
  `MediaGallery`, `SocialFeed`, `FunFactsWidget` (+ `DraggableNotes` if only used
  there), their queries in `lib/queries.ts` (`getFestivalPageData` media/social/
  funFacts), and the pipeline scripts `media_fetcher.py`,
  `fun_facts_generator.py`. Clean up `app/festival/[slug]/page.tsx` imports/JSX.
- **Expand lineup analysis** (`components/LineupAnalysis.tsx`) — add all four:
  1. **Genre breakdown** (distribution, dominant genres, diversity score)
  2. **Popularity & discovery** (headliner vs rising mix, avg popularity, hidden gems)
  3. **Schedule conflicts** (overlapping must-see sets per stage, per-day density)
  4. **Comparisons** (vs past years / similar festivals)

## #5 — Footer

New global footer (rendered in `app/layout.tsx`). Link groups:
- **Site nav:** Festivals, About, Search, Status.
- **Legal/info:** Privacy, Terms, data-source attribution (Spotify, Unsplash, etc.).
- **Social/creator:** **an9.dev**, GitHub repo, X/socials.
- **Accessibility shortcut:** button that opens the #6 a11y panel.

## #8 — Search

Current: `/api/search` → `searchAll`/`searchSuggest` RPC (trigram + ranking,
`db/migrations/20260626_v3_3_search_ranking.sql`).

- **Location search:** exact city/state match first, then **radius fallback** via
  existing lat/lng (geocode query → festivals within N miles, ordered by
  distance). Output the location AND nearby festivals.
- **Genre search:** return **both** matching artists and festivals whose lineup
  skews that genre (artists `genres[]`, festivals `tags[]`).
- **"Best-fit modern search," not literal bloom filters:** typo tolerance,
  synonyms, geo, genre, ranking, autocomplete. Skip bloom filters unless a clear
  win (note why if skipped). Extend the SQL RPC + `app/api/search/route.ts`.

## #9 — Make-your-wallpaper (rebuild `components/WallpaperStudio.tsx`)

Current studio is a single day-schedule canvas that defaults **all** sets
selected and still renders the stale brand `"festivalanalyzer"`. Rebuild to:

- **Start empty:** everything unchecked (flip the `setChosen(new Set(daySets…))`
  default). Provide an **"add all headliners"** one-tap shortcut.
- **Lock-screen geometry (strict 3 zones):** top third = negative space for
  clock/widgets; **center = artist list**; bottom third = reserved for OS UI
  overlays (keep clear). Artists centered.
- **Max ~40 artists** with auto-scaling text (font shrinks as count grows).
- **Filters/dropdowns:** by stage (if stages exist), genre, and a sort toggle
  (popularity / alphabetical).
- **Desktop layout:** **controls left, large phone-shaped preview pinned right**,
  compact, fits one screen with no scroll. Preview is the focus.
- **Mobile:** wallpaper fills the screen; a **pull-up bottom-sheet drawer** holds
  filters/options. Optimize mobile after desktop is solid.
- **Color customization:** themed presets + light/dark base + a custom
  background/text color picker.
- **Branding:** small **Soundcheck logo + wordmark, bottom-center** (in the safe
  zone). Remove the stale `"festivalanalyzer"` string.
- **Export:** download PNG at phone resolution (existing 1170×2532 canvas is fine;
  `html-to-image` acceptable if moving off raw canvas).

---

## Out of scope / deferred
- Real auth + cross-device settings sync (localStorage only for now).
- Apple Music playback (keep Spotify embed only).
- External search engine (Typesense/Meili) — stay on Postgres unless it caps out.
