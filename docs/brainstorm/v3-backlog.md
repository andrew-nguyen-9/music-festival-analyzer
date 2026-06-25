# v3 backlog — seeded at v2 close-out (WORKFLOW gate h)

Carried over from v2. This is a seed, not a plan — it captures the follow-ups and
ideas surfaced during v2 so nothing is lost. Promote items into
[`docs/planning/v3/PLAN.md`](../planning/v3/PLAN.md) at the v3 kickoff.

## Post-ship follow-ups (merged-then-tracked from v2.11)
These were deploy/secret/browser-gated and could not be verified pre-merge; they
were tracked rather than blocking the v2 → main merge (see
[`docs/archive/v2/PHASE_QA.md`](../archive/v2/PHASE_QA.md)).

- **Live performance budgets** — Lighthouse + Web Vitals (LCP/CLS/INP) against the
  prod deploy; confirm v2.10 budgets hold. Run `/benchmark` + Lighthouse.
- **Post-deploy canary** — `/canary` green after the prod deploy.
- **PWA install + offline** — installs on HTTPS prod; schedule/lineup usable
  offline; service worker caches as designed (v2.7).
- **Spotify playlists e2e** — full PKCE login → real per-day playlist in a user's
  library. Enabling v2.9 in prod needs **two** things, not one: (1) set
  `NEXT_PUBLIC_SPOTIFY_CLIENT_ID` + register `${origin}/spotify/callback`, and
  (2) **re-run `spotify_sync.py`** so `artist_spotify_cache.top_tracks` is
  populated — until v2.11's bug_001 fix it was hard-coded null, so the button
  errored with "No cached tracks". The fix is shipped but unverified against live
  Spotify; a sync run + one playlist creation confirms it. (Shipped disabled.)
- **Prod artist-slug resolution** — local QA hit 404s on `/artist/<id-hash>` links
  (local snapshot had unresolvable slugs). Verify lineup → artist links resolve on
  prod data, and that the new square-portrait hero renders with real images.
- **v2.3 live DB rollout** — if not already applied: run `scripts/finish_v2.sh`
  (3 migrations + geocode/validate) with `psql` + `DATABASE_URL`. Offline
  self-tests already pass.

## Deferred design/architecture (from v2 notes)
- **Favorites server-sync** — currently device-local IndexedDB (v2.7.4 background
  sync was N/A: no user-write backend). Needs a user-data backend; natural v3 work.
- **Edge-runtime conversion** — v2.10.1 skipped converting `force-dynamic` +
  supabase-js pages to the edge runtime (risky, marginal without measured need).
  Revisit with real Web Vitals data.
- **Domain check** — README/DEPLOYMENT say prod is `festival.an9.dev` (custom
  domain) but the v2.11 close-out answer said vercel.app subdomain. Reconcile which
  is canonical (affects the Spotify redirect URI when v2.9 is enabled).

## Scale + intelligence themes
- Many-festival ingestion (toward 200+ festivals).
- `pg_trgm` search at scale.
- Artist recommendations ("if you like X…").
- Social / editorial depth.
