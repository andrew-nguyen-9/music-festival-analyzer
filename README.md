# Soundcheck

An autonomous, pipeline-driven web app surfacing artist and lineup intelligence for
US music festivals. Starts with Lollapalooza, scales toward 200+ festivals. Editorial
UI, real streaming-data integration, AI-generated insights.

**Live:** [festival.an9.dev](https://festival.an9.dev)

---

## Stack

| Layer | Tool |
|-------|------|
| Frontend | Next.js 15 (App Router), Tailwind CSS, Framer Motion |
| Backend / DB | Supabase (Postgres + auto-REST, RLS) |
| Pipeline | Python 3.11, GitHub Actions cron |
| Music data | Spotify Web API (server-side sync → Supabase cache) |
| Media | Unsplash CDN |
| AI | Anthropic Claude API (fun facts) |
| Hosting | Vercel (frontend) + Supabase (data) |

The frontend reads **cached data from Supabase via the anon key only** — no client-side
Spotify calls, no service-role key in the browser.

---

## Repository structure

The repo root **is** the Vercel project root.

```
/
├── app/                 # Next.js App Router pages (/, /festival/[slug], /artist/[slug], …)
├── components/          # React components
├── lib/                 # Supabase client, queries, types, theming — all DB access lives here
├── pipeline/            # Python ETL (scrapers, enrichers, generators); --festival targetable
├── db/                  # schema.sql, seeds, timestamped migrations
├── docs/                # see docs/README.md (workflow, plan, deployment, design, api)
├── .github/workflows/   # ci.yml (typecheck + build on PR), etl_daily.yml (pipeline cron)
├── vercel.json          # framework pin (Next.js)
├── CLAUDE.md            # repo instructions for Claude Code
└── README.md
```

---

## Getting started

**Prerequisites:** Node.js 20+, Python 3.11+, a Supabase project.

```bash
# Frontend (from repo root)
npm install
cp .env.local.example .env.local   # fill in the two NEXT_PUBLIC_SUPABASE_* values
npm run dev                         # http://localhost:3000

# Pipeline
cd pipeline
pip install -r requirements.txt
cp .env.example .env                # fill in backend secrets (service-role key, Spotify, …)
python artist_enricher.py --festival lollapalooza --year 2026
```

The app builds and renders even with **no** Supabase env vars — it degrades to empty
states (`lib/supabase.ts`), so `npm run build` is secret-free.

### Environment variables

| Where | Vars | Notes |
|-------|------|-------|
| Frontend (`.env.local`, Vercel) | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Public, read-only (RLS-enforced). |
| Pipeline (`pipeline/.env`, GitHub Actions) | `SUPABASE_SERVICE_ROLE_KEY`, `SPOTIFY_*`, `UNSPLASH_*`, `ANTHROPIC_API_KEY` | Server-only. **Never** committed or sent to the browser. |

See `pipeline/.env.example` and `.env.local.example` for the full templates.

---

## Deployment

Vercel **Git integration**: push to `main` → production (festival.an9.dev); every PR →
preview URL. CI (`.github/workflows/ci.yml`) typechecks + builds on PRs before merge.
Full setup, env-var checklist, and verification steps in
[`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md).

---

## Data pipeline

Python scripts under `pipeline/`, run on GitHub Actions cron (`etl_daily.yml`) or
locally. All accept `--festival {slug}`, use `tenacity` retries + `rich` output, and
upsert idempotently (safe to re-run). Key scripts: `festival_scraper.py`,
`artist_enricher.py`, `media_fetcher.py`, `fun_facts_generator.py`,
`lineup_scraper.py`, `schedule_scraper.py`.

---

## Working model

All work follows the `v[phase].[segment].[task]` model in
[`docs/WORKFLOW.md`](./docs/WORKFLOW.md). **v2 shipped as `v2.0.0`** (archived under
[`docs/archive/v2/`](./docs/archive/v2/)); next phase is **v3** (stub in
[`docs/planning/v3/`](./docs/planning/v3/)). All phases in
[`docs/ROADMAP.md`](./docs/ROADMAP.md). Never commit to `main` directly. v1 is frozen
under `docs/archive/v1/`.
