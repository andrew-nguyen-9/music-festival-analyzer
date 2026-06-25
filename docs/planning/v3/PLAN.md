# v3 — Scale + Intelligence (PLAN)

> Operating model: [`docs/WORKFLOW.md`](../../WORKFLOW.md) (phase → segment → task,
> `v[p].[s].[t]`). Phase index: [`docs/ROADMAP.md`](../../ROADMAP.md). Prior phase:
> [`docs/archive/v2/`](../../archive/v2/). Backlog seed:
> [`docs/brainstorm/v3-backlog.md`](../../brainstorm/v3-backlog.md).

## North star
v2 made one festival (Lollapalooza) excellent. **v3 makes _hundreds_ of festivals
excellent, and makes the product smart about each user.** Two pillars:

1. **Scale** — ingest and keep 200+ US festivals accurate, searchable, and fast.
2. **Intelligence** — accounts, cross-device data, recommendations, and
   personalization that turn a directory into a planning tool.

A festival page should be as good for a 3,000-cap regional fest as it is for
Lollapalooza, and the home page should know who you are.

## Success criteria (phase-level exit)
- ≥ 200 festivals live, each passing the v2.3 validation gate (dates, coords,
  lineup, schedule where available) — zero "stub" rows in production.
- Cross-festival search returns ranked, typo-tolerant results in < 150 ms p95.
- Signed-in users get favorites/playlists synced across devices, plus per-user
  artist + festival recommendations with a measurable engagement lift.
- All v2 deploy-gated checks (Lighthouse/Web Vitals budgets, `/canary`, PWA
  install/offline, Spotify e2e) green in CI/CD, not just "tracked."

---

## Segment map (dependency-ordered)

Segment `0` is foundation/restructure, as always. Later segments may run in
parallel once their dependencies land; the numbering is the recommended order.

| Seg | Name | Depends on | One-line goal |
|-----|------|-----------|---------------|
| v3.0 | Foundation & ingestion framework | — | Generalize the data model + a source-adapter pipeline for many festivals. |
| v3.1 | Data quality & backfill | v3.0 | Clear v2 debt; make the validation gate block CI. |
| v3.2 | Multi-festival ingestion at scale | v3.0, v3.1 | Onboard 200+ festivals via adapters + a source registry. |
| v3.3 | Search at scale | v3.0 | `pg_trgm`/FTS cross-festival search, ranked + typo-tolerant, UI + API. |
| v3.4 | Accounts & user-data backend | v3.0 | Supabase Auth; favorites/playlists move from device-local to synced. |
| v3.5 | Spotify deepening | v3.4 | Finish playlist e2e; import top artists; saved-playlist history. |
| v3.6 | Recommendations engine | v3.2, v3.4, v3.5 | Artist similarity + per-user lineup/festival recs. |
| v3.7 | Discovery & personalization UI | v3.3, v3.6 | "For you" home, recommended festivals, saved/upcoming. |
| v3.8 | Notifications & engagement | v3.4 | Lineup-change + set-time + favorite-added alerts (web push / email). |
| v3.9 | Social & editorial depth | v3.2 | Editorial content model, festival guides, artist spotlights, sharing. |
| v3.10 | Performance at scale | v3.2, v3.3 | ISR/caching for many festivals, image pipeline, search latency budgets. |
| v3.11 | Observability & reliability | v3.2 | Pipeline freshness dashboards, error tracking, alerting. |
| v3.12 | Deploy-gated verification (v2 carryover) | v3.10 | Lighthouse/Web Vitals, `/canary`, PWA, Spotify e2e — green in CI/CD. |
| v3.13 | Phase finalize | all | Resolve open decisions, run phase-close gates, merge to `main`, seed v4. |

---

## Segments in detail

### v3.0 — Foundation & ingestion framework
**Goal:** stop hand-coding per-festival pipeline scripts; make adding a festival a
config + adapter, not a code fork.
**Tasks (indicative):**
- Generalize the schema for many festivals/years (provenance, source IDs, per-row
  confidence already started in v2.3 — extend).
- A `sources` registry + `SourceAdapter` interface (scrape | API | manual-seed),
  with a uniform normalize → validate → upsert path. Keep `--festival {slug}`.
- Ingestion run-log table (what ran, when, rows touched, errors) for observability.
- Migrations additive/reversible; RLS public-read on any new table.
**Exit:** Lolla + 2 pilot festivals ingest through the new adapter path with no
per-festival Python; run-log populated.

### v3.1 — Data quality & backfill
**Goal:** clear the debt the v2.3 live validation surfaced; make quality enforced.
**Tasks:**
- Backfill dates for the ~22 date-less festivals or flag genuinely-TBA ones
  (`dates_estimated`). Geocode the 2 missing-coords festivals.
- Merge the known artist duplicate groups (`adela`, `roz`) + a general dedupe pass.
- Promote `validate_data.py` to a **CI gate** (fails the build on regressions),
  plus a freshness check (no festival stale > N days).
**Exit:** validation green across all live festivals in CI; dedupe report clean.
(See [`docs/brainstorm/v3-backlog.md`](../../brainstorm/v3-backlog.md) → Data quality.)

### v3.2 — Multi-festival ingestion at scale
**Goal:** 200+ festivals live and maintained.
**Tasks:**
- Write adapters for the priority festival sources (official sites, APIs,
  aggregators). Rate-limit-aware (tenacity), idempotent upserts.
- Per-source confidence + conflict resolution (coalesce-forward, like Spotify cache).
- Backfill batches; daily cron scales to the full set without timing out (shard jobs).
**Exit:** ≥ 200 festivals, each passing v3.1's gate; cron completes within budget.

### v3.3 — Search at scale
**Goal:** find any festival/artist fast, across the whole catalog.
**Tasks:**
- `pg_trgm` + GIN indexes; full-text across festival names, artists, locations,
  genres. Typo-tolerant, ranked (popularity + recency + proximity).
- Search API (server, Supabase-backed) + a search UI (command-palette / page).
- Empty/zero-result and "did you mean" states.
**Exit:** ranked, typo-tolerant results < 150 ms p95 over the full catalog.

### v3.4 — Accounts & user-data backend
**Goal:** the v2.7.4 deferral — favorites are device-local IndexedDB; give them a home.
**Tasks:**
- Supabase Auth (email + OAuth incl. Spotify sign-in). RLS on user-owned rows.
- `user_favorites`, `user_playlists` tables; migrate device-local favorites on
  first sign-in (merge, don't clobber). Keep working signed-out (local fallback).
**Exit:** sign in on two devices → favorites/playlists sync; signed-out still works.

### v3.5 — Spotify deepening
**Goal:** finish what v2.9 started, now that there's an account to hang it on.
**Tasks:**
- Complete the playlist e2e: register `${origin}/spotify/callback`, verify
  user-token track resolution (shipped in v2.11 follow-up), save playlist history.
- "Connect Spotify" → import top artists/genres → highlight them in lineups.
- Token refresh + revoke handling.
**Exit:** a signed-in user creates a per-day playlist end-to-end and sees their
top artists flagged across festival lineups.

### v3.6 — Recommendations engine
**Goal:** "if you like X…" and "artists you should see at this festival."
**Tasks:**
- Artist-similarity signal: genre overlap + Spotify audio features + co-lineup
  graph (artists who share bills). Precompute neighbors nightly.
- Per-user recs from favorites + Spotify import; per-festival "don't miss" list.
- Cold-start (no data) falls back to popularity + genre.
**Exit:** recs exist for every artist and every signed-in user; offline-eval
(precision@k vs a holdout) beats the popularity baseline.

### v3.7 — Discovery & personalization UI
**Goal:** a home page that knows you.
**Tasks:**
- "For you" home: recommended festivals (by taste + geography + season), upcoming
  favorites, saved searches.
- Per-festival personalized lineup view ("your picks" pre-highlighted).
- Respect signed-out (generic editorial home) + `prefers-reduced-motion`.
**Exit:** signed-in home is personalized and measurably more engaging (CTR) than
the generic home.

### v3.8 — Notifications & engagement
**Goal:** bring users back when something they care about changes.
**Tasks:**
- Lineup-change alerts (favorite artist added/dropped), set-time reminders,
  pre-festival countdown. Web Push (PWA) + email; per-user opt-in + preferences.
- A change-detection layer on the ingestion run-log (diff lineups between runs).
**Exit:** a favorited-artist lineup change fires a push/email to opted-in users.

### v3.9 — Social & editorial depth
**Goal:** content that makes the site worth visiting between festivals.
**Tasks:**
- Editorial content model (festival guides, artist spotlights, "best sets"),
  authored + AI-assisted (Claude). Expand the social feed beyond stubs.
- Shareable artifacts (extend the v2.8 wallpaper: shareable lineup cards, recs).
**Exit:** every flagship festival has a guide; spotlights render; sharing works.

### v3.10 — Performance at scale
**Goal:** fast with 200+ festivals and personalization.
**Tasks:**
- ISR/`revalidate` + runtime caching for festival/artist pages; cache-tag
  invalidation on ingest. Image pipeline (sized, CDN, blur placeholders).
- Search + recs latency budgets; revisit the v2.10.1 edge-runtime deferral with
  real Web Vitals data.
**Exit:** Web Vitals budgets hold at catalog scale; page TTFB within budget.

### v3.11 — Observability & reliability
**Goal:** know when data goes stale or a source breaks before users do.
**Tasks:**
- Pipeline freshness + success dashboards off the run-log; error tracking
  (Sentry-style) frontend + pipeline; alerting on failed/stale ingests.
- SLOs for ingestion freshness + search/recs latency.
**Exit:** a broken source or stale festival raises an alert, not a user bug report.

### v3.12 — Deploy-gated verification (v2 carryover)
**Goal:** make the v2 "tracked follow-ups" actual CI/CD gates.
**Tasks:**
- Lighthouse + Web Vitals budgets in CI; post-deploy `/canary`; PWA
  install/offline e2e; full Spotify login→playlist e2e (against a test account).
**Exit:** all four gates green in the pipeline; no "verify later" left.

### v3.13 — Phase finalize
**Goal:** close v3 the way v2 closed.
**Tasks:** resolve open decisions, run WORKFLOW §3 gates (QA, `/code-review ultra`,
merge `v3 → main`, tag `v3.0.0`, prune branches, reconcile + archive docs to
`docs/archive/v3/`, brainstorm v4).
**Exit:** `v3.0.0` on `main`; docs archived; `docs/brainstorm/v4-backlog.md` seeded.

---

## Open decisions (resolve at v3 kickoff)
- **Auth provider** — Supabase Auth (keeps one vendor) vs Clerk/Auth0. Default:
  Supabase Auth + Spotify OAuth.
- **Festival source strategy** — per-site scrapers vs a paid aggregator API vs
  hybrid. Affects v3.2 cost + reliability.
- **Recommendations approach** — heuristic (genre/feature/graph) first vs an
  embedding/vector model (pgvector). Default: heuristic first, vector later.
- **Notifications channel priority** — web push vs email first.
- **Festival scope** — US-only (current) vs expand. Default: deepen US first.

## Carryover from v2 (folded into the segments above)
Deploy-gated verification → v3.12 · favorites server-sync → v3.4 · Spotify e2e →
v3.5 · edge-runtime revisit → v3.10 · data backfill/dedupe → v3.1 · domain
canonicalization (`festival.an9.dev`) → v3.0 housekeeping. Full list in
[`docs/brainstorm/v3-backlog.md`](../../brainstorm/v3-backlog.md).
