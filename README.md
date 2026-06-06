# Festival Analyzer

An autonomous, data-pipeline-driven web app that surfaces artist and lineup intelligence for major US music festivals. Built to be extended festival by festival, with a rich editorial UI, music streaming integrations, and AI-generated insights.

---

## Vision

**Phase 1** — Lollapalooza (Chicago). Full build, full polish.  
**Phase 2** — Top 6 US festivals: Coachella, Lollapalooza, EDC Vegas, SXSW, Ultra Miami, Governor's Ball.  
**Phase 3** — Full US festival list via [Wikipedia scrape](https://en.wikipedia.org/wiki/List_of_music_festivals_in_the_United_States).

---

## Tech Stack

| Layer | Tool | Why |
|-------|------|-----|
| Frontend | Next.js 14 (App Router) | SSR, ISR, great DX, Vercel-native |
| Styling | Tailwind CSS + Framer Motion | Editorial animations, scroll reveals |
| Hosting | Vercel | Free tier, global CDN, env vars |
| Database | Supabase (Postgres) | Free tier, REST API auto-generated, realtime |
| Object storage | Supabase Storage | Photos, festival assets |
| ETL pipeline | Python 3.11 + GitHub Actions | Scheduled cron, zero infra cost |
| Music APIs | Spotify Web API + Apple Music API | Artist metadata, genre, preview links |
| Media | Unsplash API | Free high-res festival photography |
| Social feeds | Instagram Basic Display + X (Twitter) API v2 | Per-festival feed embeds |
| AI features | Anthropic Claude API (claude-sonnet-4-20250514) | Fun facts generator, artist bios |
| Search | Supabase full-text search (pg_trgm) | Zero extra infra, fast enough for Phase 1–2 |

---

## Repository Structure

```
festival-analyzer/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md        # Full system design
│   ├── API_REFERENCE.md       # All external APIs used
│   ├── DB_SCHEMA.md           # Supabase table designs
│   ├── PIPELINE.md            # ETL agent documentation
│   └── UI_SPEC.md             # Design system + component guide
├── pipeline/
│   ├── festival_scraper.py    # Wikipedia → festivals table
│   ├── artist_enricher.py     # Spotify/Apple Music → artists table
│   ├── media_fetcher.py       # Unsplash → media table
│   ├── feed_syncer.py         # IG + X feeds per festival
│   ├── fun_facts_generator.py # Claude API → fun facts table
│   ├── scheduler.py           # Local dev runner
│   └── requirements.txt
├── db/
│   ├── schema.sql             # Full Supabase schema
│   ├── seed_lolla.sql         # Lollapalooza seed data
│   └── migrations/
├── frontend/
│   ├── app/
│   │   ├── page.tsx           # Festival index (search + filter)
│   │   ├── festival/[slug]/
│   │   │   └── page.tsx       # Individual festival page
│   │   └── artist/[slug]/
│   │       └── page.tsx       # Artist detail page
│   ├── components/
│   │   ├── FestivalCard.tsx
│   │   ├── ArtistCard.tsx
│   │   ├── LineupGrid.tsx
│   │   ├── MusicPlayerToggle.tsx
│   │   ├── FunFactsWidget.tsx
│   │   ├── SocialFeed.tsx
│   │   └── SearchBar.tsx
│   ├── lib/
│   │   ├── supabase.ts
│   │   ├── spotify.ts
│   │   └── applemusic.ts
│   └── public/
└── .github/
    └── workflows/
        ├── etl_daily.yml      # Daily artist + media refresh
        ├── etl_weekly.yml     # Weekly festival list refresh
        └── deploy.yml         # Vercel deploy on push
```

---

## Getting Started

### Prerequisites
- Node.js 20+
- Python 3.11+
- Supabase account (free)
- Vercel account (free)
- Spotify Developer account
- Apple Music MusicKit JS key
- Anthropic API key
- Unsplash API key

### Local Setup

```bash
# Clone and install frontend deps
git clone https://github.com/YOUR_USERNAME/festival-analyzer
cd festival-analyzer/frontend
npm install

# Set up Python pipeline
cd ../pipeline
pip install -r requirements.txt

# Copy env files
cp .env.example .env.local
```

### Environment Variables

```
# Supabase
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Spotify
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=

# Apple Music
APPLE_MUSIC_KEY_ID=
APPLE_MUSIC_TEAM_ID=
APPLE_MUSIC_PRIVATE_KEY=

# Anthropic
ANTHROPIC_API_KEY=

# Unsplash
UNSPLASH_ACCESS_KEY=

# Social
INSTAGRAM_ACCESS_TOKEN=
TWITTER_BEARER_TOKEN=
```

---

## Data Pipeline

All pipeline scripts run as GitHub Actions on cron schedules. They can also be triggered manually via `pipeline/scheduler.py` for local dev.

| Script | Schedule | Purpose |
|--------|----------|---------|
| `festival_scraper.py` | Weekly (Mon 6am CT) | Scrape Wikipedia, upsert festivals |
| `artist_enricher.py` | Daily (3am CT) | Enrich artist rows with Spotify/Apple data |
| `media_fetcher.py` | Daily (4am CT) | Pull Unsplash photos per festival |
| `feed_syncer.py` | Every 6 hours | Sync latest IG + X posts per festival |
| `fun_facts_generator.py` | On lineup change | Generate AI fun facts via Claude API |

---

## UI Design Reference

Inspiration sources:
- https://www.awwwards.com/thefirstthelast/ — full-bleed editorial, large type, scroll-driven reveals
- https://www.awwwards.com/sites/how-f1-has-evolved-since-1950 — data-driven storytelling, timeline layout

Key design principles:
- Full-bleed festival hero photos (Unsplash)
- Large display typography — festival name at 80–120px
- Scroll-triggered animations via Framer Motion
- Dark-first with festival-specific accent colors
- Minimal chrome — content leads

---

## Scalability Notes

All free tiers used in Phase 1–2 comfortably handle this load:

| Service | Free tier limit | Expected usage |
|---------|-----------------|----------------|
| Vercel | 100GB bandwidth/mo | ~1–2GB |
| Supabase | 500MB DB, 1GB storage | ~50MB DB, 200MB storage |
| GitHub Actions | 2000 min/mo | ~300 min/mo |
| Spotify API | 1000 req/day without auth | ~200 req/run |
| Unsplash | 50 req/hour | ~30 req/run |

When scaling to Phase 3 (200+ festivals), the only thing that needs upgrading is Supabase storage (still cheap — $25/mo Pro plan). Everything else stays free.

---

## Contributing

This project is built to grow. To add a new festival:
1. Run `festival_scraper.py --festival "Festival Name"` to bootstrap it
2. Add a seed SQL file in `db/`
3. The ETL pipeline will handle the rest automatically
