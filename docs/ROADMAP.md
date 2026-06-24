# ROADMAP.md — Festival Analyzer Phases

A bird's-eye view of every phase. Detail for the active phase lives in
`docs/planning/v[p]/PLAN.md`. The operating model is `docs/WORKFLOW.md`.

| Phase | Version | Theme | State |
|-------|---------|-------|-------|
| 1 | `v1.0.0` | Initial build — Lollapalooza, pipeline, 3 page templates, Supabase wiring | **Frozen / archived** (`docs/archive/v1/`) |
| 2 | `v2.x` | Productionize + reinvent — deploy, Spotify, accurate data, bold redesign, PWA, killer features | **Active** → `docs/planning/v2/PLAN.md` |
| 3 | `v3.x` | Scale + intelligence — more festivals, search at scale, recommendations | Backlog (seeded from v2 close-out brainstorm) |

---

## v1.0.0 — what exists (frozen baseline)

- Next.js 14 App Router frontend, ~33 components, 3 routes (`/`, `/festival/[slug]`, `/artist/[slug]`).
- Resilient Supabase data layer (`lib/supabase.ts`, `lib/queries.ts`) — empty-safe, builds with no keys.
- Runtime festival theming from `accent_color`.
- Python pipeline: festival/artist/schedule scrapers, enrichers, fun-facts, media.
- Spotify embeds (auth-free iframes) only; no real Spotify API integration yet.
- Lives in nested `festival-analyzer/`; repo root cluttered with stray artifacts.

## v2.x — productionize + reinvent (active)

Foundation-first, then redesign, then killer features. Eleven segments,
dependency-ordered. Full breakdown in `docs/planning/v2/PLAN.md`.

```
v2.0  Foundation        flatten repo, clean, .github/Vercel, first live deploy
v2.1  Data layer        Supabase audit, RLS/indexes, query consolidation, cache tables
v2.2  Spotify sync      server sync worker → Supabase cache (2026 API reality)
v2.3  Pipeline accuracy accurate lineups / dates / locations
v2.4  Artist page       rebuild, portrait normalization, richer content
v2.5  Design system     investigative-journalism direction → new design language
v2.6  UI rebuild        apply redesign, View Transitions, predictive prefetch
v2.7  PWA / offline      Workbox SWR cache, IndexedDB, background sync, installable
v2.8  Phone background   day schedule + stage locations → shareable image
v2.9  Smart playlists    favorited artists → auto Spotify playlist
v2.10 Edge + perf        edge compute, Core Web Vitals, canary, phase close-out
```

## v3.x — scale + intelligence (backlog)

Direction only; finalized at v2 close-out (gate **h**). Likely themes: many-festival
ingestion, `pg_trgm` search at scale, artist recommendations, social/editorial depth.
