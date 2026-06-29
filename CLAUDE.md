# CLAUDE.md — Soundcheck

This file instructs Claude Code on how to work in this repository.

> **Working model (read first):** all work follows the phase → segment → task
> model in [`docs/WORKFLOW.md`](./docs/WORKFLOW.md). **v2 shipped as `v2.0.0`**
> (archived under [`docs/archive/v2/`](./docs/archive/v2/)). The next phase is
> **v3** — stub at [`docs/planning/v3/PLAN.md`](./docs/planning/v3/PLAN.md),
> backlog seed at [`docs/brainstorm/v3-backlog.md`](./docs/brainstorm/v3-backlog.md);
> cut the v3 phase branch off `main` before starting work. Phases:
> [`docs/ROADMAP.md`](./docs/ROADMAP.md). Docs index: [`docs/README.md`](./docs/README.md).

---

## Project Overview

Soundcheck is an autonomous, pipeline-driven web app surfacing artist and
lineup intelligence for US music festivals. It starts with Lollapalooza and scales
to 200+ festivals.

## Stack Summary

- **Frontend**: Next.js 14 (App Router), Tailwind CSS, Framer Motion
- **Backend/DB**: Supabase (Postgres + auto-REST API)
- **Pipeline**: Python 3.11 scripts, run on GitHub Actions cron
- **Music APIs**: Spotify Web API (server-side sync worker → Supabase cache), Apple Music (MusicKit JS)
- **Media**: Unsplash API
- **AI**: Anthropic Claude API (fun facts generator)
- **Hosting**: Vercel (frontend) + Supabase (data)

## Repo structure

> **Flattened in v2.0.** The repo root **is** the Vercel project root; the old
> nested `festival-analyzer/` wrapper is gone. v1 artifacts are frozen under
> `docs/archive/v1/`.

```
/ (repo root = Vercel project root)
├── app/  components/  lib/   ← Next.js frontend (no public/ yet — add when static assets exist)
├── pipeline/                 ← Python ETL
├── db/                       ← schema, seeds, migrations
├── docs/                     ← see docs/README.md
├── .github/workflows/        ← ci.yml (PR typecheck+build), etl_daily.yml (cron)
├── vercel.json  CLAUDE.md  README.md
```

## Versioning & branches (summary — full rules in WORKFLOW.md)

- `v[phase].[segment].[task]` — e.g. `v2.1.3`.
- Phase = branch off `main` (`v2`). Segment = sub-branch off the phase (`v2.1-data-layer`). Task = a commit.
- **Never commit to `main` directly.** Segments merge to their phase branch; only a closed phase merges to `main`.
- Segment gates: build → test → `/qa` → `/code-review` → commit → merge to phase branch → delete sub-branch.
- Prior work is frozen as **v1.0.0** under `docs/archive/v1/`.

## Conventions

### Python pipeline
- All scripts accept `--festival {slug}` for targeted runs.
- Use `tenacity` for all external API calls (3 retries, exponential backoff).
- Use `rich` for console output.
- Secrets via `python-dotenv` (`.env`, never committed).
- Upsert on conflict — scripts are idempotent and safe to re-run.

### TypeScript / Next.js
- App Router only (no Pages Router).
- Server Components by default; `"use client"` only when needed (interactivity, localStorage).
- All Supabase queries in `lib/` helpers — no raw fetches in components.
- **No client-side Spotify calls** — the frontend reads cached artist data from Supabase only (see v2.2).
- Festival theme color derived at runtime from `festival.accent_color`.
- Animations via Framer Motion / View Transitions; respect `prefers-reduced-motion`.
- Design language follows [`docs/design/DESIGN_DIRECTION.md`](./docs/design/DESIGN_DIRECTION.md) (system finalized in v2.5).

### Database
- All writes go through the service role key (pipeline/server only).
- Frontend uses the anon key (public reads only, enforced by RLS).
- New tables need RLS enabled + public-read policy.
- Migrations go in `db/migrations/` with a timestamp prefix; additive and reversible.
- External-API data (e.g. Spotify) is cached in dedicated cache tables with `fetched_at` + TTL.

## Tooling

- **Token efficiency:** RTK (auto via hook), caveman + ponytail modes on by default.
- **Code navigation:** graphify (`graphify-out/`), context7 for library docs.
- **QA/review:** `/qa`, `/code-review` (`ultra` for risky work), `/design-review`, chrome-devtools, playwright.
- **Deploy:** Vercel (config in v2.0).

## Do Not

- Do not commit `.env` files or any secret.
- Do not use the Supabase service role key in frontend code.
- Do not call the Spotify API from the client — read the Supabase cache.
- Do not store Unsplash images locally — always use Unsplash CDN URLs.
- Do not make direct DB writes from the frontend — use the pipeline or Supabase functions.
- Do not hardcode festival data in components — always pull from Supabase.
- Do not commit to `main` directly or merge a segment to `main` — follow `WORKFLOW.md`.
