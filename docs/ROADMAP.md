# ROADMAP.md — Festival Analyzer Phases

A bird's-eye view of every phase. Detail for the active phase lives in
`docs/planning/v[p]/PLAN.md`. The operating model is `docs/WORKFLOW.md`.

| Phase | Version | Theme | State |
|-------|---------|-------|-------|
| 1 | `v1.0.0` | Initial build — Lollapalooza, pipeline, 3 page templates, Supabase wiring | **Frozen / archived** (`docs/archive/v1/`) |
| 2 | `v2.0.0` | Productionize + reinvent — deploy, Spotify, accurate data, bold redesign, PWA, killer features | **Shipped / archived** (`docs/archive/v2/`) |
| 3 | `v3.x` | Scale + intelligence — 200+ festivals, search at scale, accounts, recommendations, personalization | **Planned** → `docs/planning/v3/PLAN.md` (14 segments) |

---

## v1.0.0 — what exists (frozen baseline)

- Next.js 14 App Router frontend, ~33 components, 3 routes (`/`, `/festival/[slug]`, `/artist/[slug]`).
- Resilient Supabase data layer (`lib/supabase.ts`, `lib/queries.ts`) — empty-safe, builds with no keys.
- Runtime festival theming from `accent_color`.
- Python pipeline: festival/artist/schedule scrapers, enrichers, fun-facts, media.
- Spotify embeds (auth-free iframes) only; no real Spotify API integration yet.
- Lives in nested `festival-analyzer/`; repo root cluttered with stray artifacts.

## v2.x — productionize + reinvent (active)

Foundation-first, then redesign, then killer features. Twelve segments,
dependency-ordered. Full breakdown in `docs/planning/v2/PLAN.md`.

```
v2.0  Foundation        flatten repo, clean, .github/Vercel, first live deploy   ✅ done
v2.1  Data layer        Supabase audit, RLS/indexes, query consolidation, cache tables  ✅ done
v2.2  Spotify sync      server sync worker → Supabase cache (2026 API reality)   ✅ done
v2.3  Pipeline accuracy accurate lineups / dates / locations                     ✅ done (live rollout pending)
v2.4  Artist page       rebuild + square-portrait hero (reframed in v2.11)       ✅ done
v2.5  Design system     investigative-journalism direction → new design language ✅ done ("The Dossier")
v2.6  UI rebuild        apply redesign, View Transitions, predictive prefetch     ✅ done
v2.7  PWA / offline      SWR service worker, IndexedDB, installable                ✅ done
v2.8  Phone background   day schedule + stage locations → shareable image          ✅ done (client canvas)
v2.9  Smart playlists    favorited artists → per-day Spotify playlist (v2.11)       ✅ done (PKCE)
v2.10 Edge + perf        Core Web Vitals (next/font), web-vitals reporting, close-out ✅ done
v2.11 Phase finalize     square portrait + per-day playlists + postcss; close gates → merge to main ✅ done
```

**Progress:** v2.0–v2.11 complete (12 of 12) — phase **shipped as v2.0.0** and
merged to `main`. The deploy/secret/browser-gated checks (live Lighthouse/Web
Vitals, `/canary`, PWA install, full Spotify e2e, prod artist-slug verification)
were merged-then-tracked as post-ship follow-ups in
[`docs/brainstorm/v3-backlog.md`](./brainstorm/v3-backlog.md). The v2 close-out
record (PLAN, PHASE_QA, audits) is archived under
[`docs/archive/v2/`](./archive/v2/).

## v3.x — scale + intelligence (planned)

Full breakdown in [`docs/planning/v3/PLAN.md`](./planning/v3/PLAN.md) — **14
dependency-ordered segments** (v3.0–v3.13). North star: v2 made one festival
excellent; v3 makes 200+ festivals excellent and makes the product smart about
each user.

```
v3.0  Foundation & ingestion framework   generalized schema + source-adapter pipeline
v3.1  Data quality & backfill            clear v2 debt; validation as a CI gate
v3.2  Multi-festival ingestion at scale  200+ festivals via adapters + source registry
v3.3  Search at scale                    pg_trgm/FTS, ranked, typo-tolerant, UI + API
v3.4  Accounts & user-data backend       Supabase Auth; favorites/playlists synced
v3.5  Spotify deepening                  finish playlist e2e; import top artists
v3.6  Recommendations engine             artist similarity + per-user lineup/festival recs
v3.7  Discovery & personalization UI     "for you" home, recommended festivals
v3.8  Notifications & engagement         lineup-change + set-time + favorite alerts
v3.9  Social & editorial depth           guides, spotlights, shareable cards
v3.10 Performance at scale               ISR/caching, image pipeline, latency budgets
v3.11 Observability & reliability        freshness dashboards, error tracking, alerting
v3.12 Deploy-gated verification          v2 carryover (Lighthouse/canary/PWA/Spotify) → CI gates
v3.13 Phase finalize                     close gates → merge to main, tag v3.0.0, seed v4
```

Seed + carried-over follow-ups: [`docs/brainstorm/v3-backlog.md`](./brainstorm/v3-backlog.md).
Open decisions (auth provider, source strategy, recs approach, notification
channel, festival scope) are flagged in the PLAN for the v3 kickoff.
