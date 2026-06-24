# v2 PLAN — Productionize + Reinvent

Phase branch: **`v2`** (cut from `main`). Operating model: `docs/WORKFLOW.md`.
Design direction for the redesign segments: `docs/design/DESIGN_DIRECTION.md`.

**Goal of v2:** take the v1 baseline from "builds locally" to "deployed, accurate,
fast, offline-capable, and visually distinctive," with real Spotify integration and
two killer features (phone-background generator, smart playlists).

**Sequencing principle:** foundation first (deploy + data + accuracy), then the
redesign, then the heavy features. Ship something live early; reduce rework risk.

Legend: each segment lists its sub-branch, goal, ordered tasks (`v2.s.t`),
dependencies, and exit criteria. Tasks are commits, not branches.

---

## v2.0 — Foundation `v2.0-foundation`

**Goal:** flatten the repo to a clean Vercel-ready root, archive v1, stand up
CI/CD, and ship the first live production deploy.

**Depends on:** nothing (opens the phase).

**Tasks**
- `v2.0.1` Flatten `festival-analyzer/*` → repo root (`app/`, `components/`, `lib/`, `public/`, `pipeline/`, `db/`). Preserve git history with `git mv`.
- `v2.0.2` Archive v1 artifacts → `docs/archive/v1/` (old `HANDOFF.md`, root `schema.sql`, `festival_analyzer_architecture.svg`, `graphify-out/`). Remove stray build logs.
- `v2.0.3` Consolidate docs into the `docs/` tree (see `docs/README.md`); fix all internal links.
- `v2.0.4` `.github/` hardening: keep `etl_daily.yml`, add CI workflow (typecheck + `next build` on PR), add Vercel deploy workflow or Vercel Git integration.
- `v2.0.5` Vercel project config: root = repo root, env vars (anon key, service key as server-only), build settings, preview deploys on PR.
- `v2.0.6` Rewrite root `README.md` + `CLAUDE.md` for the new structure (CLAUDE.md target already drafted this phase).
- `v2.0.7` First production deploy; verify live URL renders Lollapalooza end-to-end.

**Exit criteria:** repo root is the Vercel project root; `main`-quality build deploys
to a live URL; v1 artifacts archived not deleted; no broken doc links; CI green on PR.

---

## v2.1 — Data layer `v2.1-data-layer`

**Goal:** make Supabase access efficient, correct, and ready to back caches.

**Depends on:** v2.0 (deployed env).

**Tasks**
- `v2.1.1` Schema audit vs. live DB; reconcile `db/schema.sql` with reality; document tables.
- `v2.1.2` RLS review — every table has RLS on + public-read policy; service-role writes only.
- `v2.1.3` Add indexes for hot query paths (festival slug, artist slug, lineup joins, popularity sort).
- `v2.1.4` Add cache tables for external data (e.g. `artist_spotify_cache`) with `fetched_at` + TTL columns — backing store for v2.2.
- `v2.1.5` Consolidate `lib/queries.ts`: dedupe queries, select only needed columns, batch where possible, keep all DB access in `lib/`.
- `v2.1.6` Regenerate/verify TS types (`lib/types.ts`) against schema.

**Exit criteria:** no N+1 query patterns on the three routes; RLS verified; cache
tables exist with TTL semantics; types match schema; queries select minimal columns.

---

## v2.2 — Spotify sync `v2.2-spotify-sync`

**Goal:** real Spotify data, resilient to the 2026 API reality, never called from the client.

**Depends on:** v2.1 (cache tables).

**2026 constraints baked in:** no bulk metadata endpoints; legacy "artist top tracks"
removed; global `/search` capped at 10 items/request; Development Mode tightened.

**Tasks**
- `v2.2.1` Server-side Spotify client (client-credentials flow) in `pipeline/` and/or a Vercel server function — secrets server-only.
- `v2.2.2` Sync worker: fetch artists **individually** in throttled `Promise.all` batches; respect rate limits with backoff (reuse `tenacity` pattern in pipeline).
- `v2.2.3` Search with offset pagination (10/page) so lesser-known acts aren't missed; fuzzy-match festival artist names → Spotify IDs.
- `v2.2.4` Write results to `artist_spotify_cache` (v2.1.4); stale-on-TTL re-fetch.
- `v2.2.5` Frontend reads **cache only** — no client-side Spotify calls. Wire `ArtistHero`/`StreamingWidget` to cached fields.
- `v2.2.6` Schedule the sync worker (GitHub Actions cron) + manual `--festival` trigger.

**Exit criteria:** artist pages show real cached Spotify data; zero client-side Spotify
requests; sync survives a rate-limit storm (verified with throttle test); names matched ≥ target accuracy.

---

## v2.3 — Pipeline accuracy `v2.3-pipeline-accuracy`

**Goal:** accurate lineups, dates, and locations — the data users trust.

**Depends on:** v2.1 (schema), can parallel v2.2.

**Tasks**
- `v2.3.1` Audit current scraper outputs vs. ground truth for Lollapalooza 2026; list error classes.
- `v2.3.2` Improve lineup sourcing (official lineup + Wikipedia reconciliation); dedupe artists; canonical names.
- `v2.3.3` Date accuracy: festival start/end + per-set times; timezone-correct storage.
- `v2.3.4` Location accuracy: venue + city + geocoded lat/lng (needed by v2.8 phone background).
- `v2.3.5` Validation pass: schema constraints + a runnable sanity check that fails on missing/contradictory dates or locations.
- `v2.3.6` Idempotent upserts confirmed; safe re-runs.

**Exit criteria:** Lollapalooza lineup/dates/locations verified correct; validation
check passes in CI; geocoded coordinates present for every stage.

---

## v2.4 — Artist page `v2.4-artist-page`

**Goal:** rebuild the artist page; solve inconsistent portrait framing.

**Depends on:** v2.2 (cached Spotify data).

**Tasks**
- `v2.4.1` Portrait normalization: consistent focal-point/centering for wildly different source images (object-fit + focal-point metadata or smart-crop).
- `v2.4.2` Richer content blocks: discography, festival appearances, stats, fun facts — laid out for the new design (coordinate with v2.5/2.6).
- `v2.4.3` Audio micro-player hooks (preview snippets) — scaffold for v2.6 polish.
- `v2.4.4` Empty/partial-data states for artists with thin Spotify coverage.

**Exit criteria:** every artist portrait reads as intentional regardless of source aspect;
page handles thin-data artists gracefully; content blocks data-driven from cache.

---

## v2.5 — Design system `v2.5-design-system`

**Goal:** define a distinctive, investigative-journalism design language. **No app
rebuild here** — this segment produces the system; v2.6 applies it.

**Depends on:** v2.4 content understanding; informs v2.6.

**Tasks**
- `v2.5.1` Finalize `docs/design/DESIGN_DIRECTION.md` into a full system: type scale, color/theming model, spacing, grid, motion language, component inventory.
- `v2.5.2` Dark-by-default palette + festival-accent theming rules.
- `v2.5.3` Motion spec: scroll-driven storytelling, View-Transitions morph rules, reduced-motion behavior.
- `v2.5.4` Design exploration (use `/frontend-design`, `/design-shotgun`, figma) — produce 2–3 variants, pick one.
- `v2.5.5` Supersede `docs/design/UI_SPEC.md`; mark v1 spec archived.

**Exit criteria:** approved design system doc + tokens; one chosen visual direction;
old UI spec superseded with a migration note.

---

## v2.6 — UI rebuild `v2.6-ui-rebuild`

**Goal:** apply the v2.5 system across all pages with native-app-grade interactions.

**Depends on:** v2.5 (system), v2.1–2.4 (data).

**Tasks**
- `v2.6.1` Rebuild `/`, `/festival/[slug]`, `/artist/[slug]` on the new system.
- `v2.6.2` View Transitions API: grid → detail image morph (native-like).
- `v2.6.3` Predictive prefetch: IntersectionObserver prefetches artist-card data before it enters viewport.
- `v2.6.4` Micro-interactions + audio micro-players (hover/long-press 30s preview) wired to cache.
- `v2.6.5` Accessibility + reduced-motion pass; `/design-review` fix loop.

**Exit criteria:** all routes on the new design; no loading spinner on intra-site
navigation (prefetch working); transitions smooth; a11y + reduced-motion verified.

---

## v2.7 — PWA / offline `v2.7-pwa-offline`

**Goal:** offline-first for the muddy-field, no-signal reality.

**Depends on:** v2.6 (stable UI surface to cache).

**Tasks**
- `v2.7.1` PWA manifest + installable (home-screen, icons, theme color).
- `v2.7.2` Service worker via Workbox: stale-while-revalidate for schedules/lineups/structural assets.
- `v2.7.3` IndexedDB for user data (starred artists, custom schedules) written offline.
- `v2.7.4` Background Sync: queue offline mutations, flush on reconnect.
- `v2.7.5` Offline UX: clear cached-vs-live indicators; no infinite spinners on dropped signal.

**Exit criteria:** app installs; core schedule/lineup usable fully offline; starring an
artist offline persists and syncs on reconnect (verified in throttled/offline test).

---

## v2.8 — Phone background generator `v2.8-phone-bg`

**Goal:** killer feature #1 — a shareable phone wallpaper of a day's schedule with stage locations.

**Depends on:** v2.3 (locations/times), v2.7 (offline user schedules), v2.6 (visual system).

**Tasks**
- `v2.8.1` Day-schedule selector: pick festival + day + chosen sets.
- `v2.8.2` Layout: set times + stage locations rendered in the v2.5 visual language, phone aspect ratios.
- `v2.8.3` Image generation (canvas/`satori`-style server render or client canvas) → downloadable/shareable.
- `v2.8.4` Location rendering uses geocoded stage data from v2.3.

**Exit criteria:** user selects a day's sets and downloads a correct, on-brand wallpaper
showing times + stage locations; works for any festival with location data.

---

## v2.9 — Smart playlists `v2.9-smart-playlists`

**Goal:** killer feature #2 — one button turns favorited artists into a Spotify playlist.

**Depends on:** v2.2 (Spotify auth + IDs), v2.7 (favorites store).

**Tasks**
- `v2.9.1` Spotify user-auth (Authorization Code + PKCE) — distinct from the client-credentials sync worker.
- `v2.9.2` From favorited artists → top tracks per artist (server-side, individual fetches, cached).
- `v2.9.3` Create playlist + batch-save via the streamlined `/me` library endpoint using Spotify URIs (single request where possible).
- `v2.9.4` UX: "Make my weekend playlist" button on a festival/day; success + open-in-Spotify state.

**Exit criteria:** authenticated user generates a real playlist in their library from
their favorites in one action; batch-save uses URI single-request path; failures handled.

---

## v2.10 — Edge + performance `v2.10-edge-perf`

**Goal:** make it feel instant, then close the phase.

**Depends on:** everything above.

**Tasks**
- `v2.10.1` Move latency-sensitive dynamic logic (countdowns, localized schedules) to edge functions.
- `v2.10.2` Core Web Vitals pass: LCP/CLS/INP budgets; image/font optimization; bundle trim.
- `v2.10.3` Lighthouse + `/benchmark` regression gate; chrome-devtools perf traces.
- `v2.10.4` Post-deploy `/canary` monitoring wired.
- `v2.10.5` Phase close-out prep: run all segment exit checks; compile phase QA list.

**Exit criteria:** Web Vitals in budget on live URL; Lighthouse target met; canary green;
ready for phase-close gates (a)–(h) in `WORKFLOW.md`.

---

## Cross-cutting (apply in every segment)

- Secrets server-only; never in client bundles or git.
- DB migrations timestamped + additive (`db/migrations/`).
- Pipeline scripts idempotent, `--festival` targetable, `tenacity` retries, `rich` output.
- Every behavior change updates its docs in the same sub-branch.
- Token efficiency on by default (RTK, caveman, ponytail).

## Open questions to resolve in-segment

- v2.2: exact name-match accuracy target + fallback when no Spotify match.
- v2.5: final visual direction (decided via design exploration, not pre-locked).
- v2.8: server render vs. client canvas for image generation (decide on perf/offline tradeoff).
- v2.9: playlist scope (per-day vs. per-weekend vs. per-festival) — confirm with product intent.
