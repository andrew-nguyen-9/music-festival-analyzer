# v2 Phase QA — close-out checklist (v2.10.5)

Status of the feature segments v2.4–v2.10 and what still needs a live environment.
All code is merged to `v2` and passes the gates runnable without infra:
**`tsc --noEmit` clean** and **`next build` green**. The items below are the ones
that need a deploy, real third-party credentials, or a browser to verify — they
feed v2.11 (phase finalize) before the merge to `main`.

## Verified here (build-time)
- Typecheck + production build green on every segment.
- No client bundle regressions — `/festival/[slug]` First Load ≈167 kB after
  routing the Spotify cache read through `/api/playlist-tracks` (keeps
  `@supabase/supabase-js` server-only).
- Feature flags degrade gracefully when unconfigured (Supabase, Spotify).

## Needs a live environment (do in v2.11)

| Area | What to verify | Needs |
|------|----------------|-------|
| v2.4 portraits | Focal framing reads well across real source images | deploy + real artist images |
| v2.6 view transitions | grid→detail morph animates (vs. the safe fallback) | a browser; falls back cleanly if unsupported |
| v2.6 prefetch | next/link IO prefetch warms artist routes | a deploy + devtools network |
| v2.7 PWA | Installs; schedule/lineup usable offline; SW caches | HTTPS deploy (SW needs prod) |
| v2.7 favorites | Star offline → persists across reload | a browser |
| v2.8 wallpaper | Canvas renders + PNG downloads correctly; fonts load | a browser |
| v2.9 playlists | Full PKCE login → real playlist in a user's library | a **Spotify app** (set `NEXT_PUBLIC_SPOTIFY_CLIENT_ID`, register `${origin}/spotify/callback`) + cache populated with `top_tracks` |
| v2.10 Web Vitals | LCP/CLS/INP in budget; Lighthouse target | a deploy + Lighthouse / `/benchmark` |
| v2.10 canary | Post-deploy `/canary` monitoring green | a deploy |

## Open product decisions — autonomous defaults taken
The PLAN flagged these as in-segment decisions. Run autonomously, so defaults were
chosen and documented; revisit in v2.11 if product disagrees.

- **v2.5 visual direction → "The Dossier"** (investigative-editorial dark). Chosen
  over Poster / Spotify-grid variants (rationale in `DESIGN_SYSTEM.md`).
- **v2.8 image generation → client canvas** (offline-capable, no server cost) over
  a server render.
- **v2.9 playlist scope → per-festival** ("Make my {festival} playlist", from
  starred artists in that lineup).

## Deliberate deviations from PLAN (with rationale)
- **v2.7.2 service worker is hand-rolled SWR, not Workbox** — the policy is small;
  no build-tool integration needed. Upgrade path noted in `public/sw.js`.
- **v2.7.4 background-sync-to-server is N/A** — the app has no user-write backend
  (RLS public-read; writes via the service-role pipeline), so favorites are
  device-local IndexedDB. Add server sync when a user-data backend lands (v3).
- **v2.10.1 edge-runtime conversion skipped** — converting `force-dynamic` +
  supabase-js pages to the edge runtime is risky and marginal without measured
  need; latency-sensitive countdown logic is already client-side. Revisit with
  real Web Vitals data.

## Then: v2.11 phase-close gates (WORKFLOW §3)
(a) `/qa` full-app · (b) `/code-review ultra` · (c) final commit · (d) merge
`v2 → main` · (e) delete branches · (f) reconcile docs · (g) archive planning ·
(h) brainstorm v3.

## v2.11 resolution (what actually shipped)
Product reviewed the autonomous defaults and **overrode three** of them:
- **v2.4 → square portrait.** `ArtistHero` reframed from a full-bleed background
  hero to a bounded square portrait + dossier metadata column.
- **v2.9 → per-day playlists** (was per-festival). The lineup is grouped by day;
  the user picks a day, falling back to the whole lineup when there's no schedule.
- v2.8 image generation **kept as client canvas** (override considered, declined).
- v2.4 portrait focal change subsumed by the square-portrait reframe.

Also in v2.11: postcss bumped to 8.5.10+ (`$postcss` override; cleared the
moderate XSS advisory). The deploy/secret/browser-gated checks above were
**merged-then-tracked** as post-ship follow-ups (see `docs/brainstorm/v3-backlog.md`)
rather than blocking the merge. v2.3 live DB rollout (`scripts/finish_v2.sh`)
ran offline self-tests (all pass); the migrations + prod write-stages are an
operator step (needs psql + `DATABASE_URL`).
