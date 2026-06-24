# CLAUDE.md — Festival Analyzer

This file instructs Claude Code on how to work in this repository.

---

## Project Overview

Festival Analyzer is an autonomous, pipeline-driven web app surfacing artist and lineup intelligence for US music festivals. It starts with Lollapalooza and scales to 200+ festivals.

## Stack Summary

- **Frontend**: Next.js 14 (App Router), Tailwind CSS, Framer Motion
- **Backend/DB**: Supabase (Postgres + auto-REST API)
- **Pipeline**: Python 3.11 scripts, run on GitHub Actions cron
- **Music APIs**: Spotify Web API, Apple Music API (MusicKit JS)
- **Media**: Unsplash API
- **AI**: Anthropic Claude API (fun facts generator)
- **Hosting**: Vercel (frontend) + Supabase (data)

## Key Files

| File | Purpose |
|------|---------|
| `db/schema.sql` | Full database schema — run in Supabase SQL editor |
| `pipeline/festival_scraper.py` | Scrapes Wikipedia → festivals table |
| `pipeline/artist_enricher.py` | Spotify/Apple Music → artists table |
| `pipeline/fun_facts_generator.py` | Claude API → fun_facts table |
| `pipeline/media_fetcher.py` | Unsplash → media table |
| `pipeline/feed_syncer.py` | IG + X posts → social_posts table |
| `.github/workflows/etl_daily.yml` | Daily pipeline GitHub Actions |
| `docs/UI_SPEC.md` | Full design system + component guide |
| `docs/API_REFERENCE.md` | All external API details + setup |

## Conventions

### Python pipeline
- All scripts accept `--festival {slug}` for targeted runs
- Use `tenacity` for all external API calls (3 retries, exponential backoff)
- Use `rich` for console output
- Secrets via `python-dotenv` (`.env` file, never committed)
- Upsert on conflict — scripts are idempotent and safe to re-run

### TypeScript / Next.js
- App Router only (no Pages Router)
- Server Components by default; `"use client"` only when needed (interactivity, localStorage)
- All Supabase queries in `lib/supabase.ts` helpers — no raw fetches in components
- Festival theme color derived at runtime from `festival.accent_color` (see `docs/UI_SPEC.md`)
- Animations via Framer Motion; respect `prefers-reduced-motion`

### Database
- All writes go through the service role key (pipeline only)
- Frontend uses anon key (public reads only, enforced by RLS)
- New tables need RLS enabled + public read policy (see `db/schema.sql` pattern)
- Migrations go in `db/migrations/` with timestamp prefix

## Common Claude Code Tasks

### Add a new festival
1. Add entry to `PRIORITY_FESTIVALS` in `pipeline/festival_scraper.py`
2. Run `python pipeline/festival_scraper.py --festival "Festival Name"`
3. Add seed data in `db/seed_{festival_slug}.sql`
4. Add Unsplash search query in `pipeline/media_fetcher.py`

### Add a new pipeline script
1. Follow the pattern in `artist_enricher.py` (argparse, supabase client, retry logic)
2. Add to `.github/workflows/etl_daily.yml` or create a new workflow

### Add a new frontend page
1. Create `frontend/app/{path}/page.tsx`
2. Add to navigation in `frontend/components/Nav.tsx`
3. Follow the festival theme pattern from `festival/[slug]/page.tsx`

### Debugging pipeline locally
```bash
cd pipeline
cp ../.env.example .env     # fill in your keys
python festival_scraper.py --priority-only   # bootstrap top 6
python artist_enricher.py --festival lollapalooza --year 2026
python fun_facts_generator.py --festival lollapalooza --year 2026
```

## Phase Roadmap

| Phase | Scope | Key work |
|-------|-------|---------|
| 1 | Lollapalooza | Full build: DB, pipeline, all 8 frontend pages, fun facts |
| 2 | Top 6 festivals | Add Coachella, EDC, SXSW, Ultra, Gov Ball; test pipeline scale |
| 3 | Full US list | Wikipedia scrape active, search scales via pg_trgm |

## Do Not

- Do not commit `.env` files
- Do not use the Supabase service role key in frontend code
- Do not store Unsplash images locally — always use Unsplash CDN URLs
- Do not make direct DB writes from the frontend — use the pipeline or Supabase functions
- Do not hardcode festival data in components — always pull from Supabase
