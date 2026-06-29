# v4 Ralph Loop — State

Tracks per-area progress so each iteration resumes cleanly. Order is locked in PLAN.md.

| # | Area | Branch | Status |
|---|------|--------|--------|
| 4 | Artist pipeline | `v4.1-artist-pipeline` | IN PROGRESS |
| 7 | Festival data quality | `v4.2-festival-data` | todo |
| 1 | Header light/dark | `v4.3-header-theme` | todo |
| 6 | Accessibility panel | `v4.4-a11y` | todo |
| 2 | Homepage | `v4.5-homepage` | todo |
| 3 | Festival page | `v4.6-festival-page` | todo |
| 5 | Footer | `v4.7-footer` | todo |
| 8 | Search | `v4.8-search` | todo |
| 9 | Wallpaper rebuild | `v4.9-wallpaper` | todo |

## #4 notes (diagnosis + fix)
- **Root cause:** Spotify 2026 API returns null popularity/followers/genres for our
  client-credentials token (verified even on Olivia Rodrigo, via /search AND /artists/{id}).
  Spotify gives only spotify_id + image. Plus sync had only run for 17/181 Lolla artists,
  and no source ever supplied bios.
- **Fix:** new `pipeline/artist_bio_enricher.py` — MusicBrainz (genres via tags +
  Wikipedia/Wikidata relation) + Wikipedia REST (bio) + Deezer (popularity proxy +
  followers + image). Writes existing `artists` columns (frontend reads them as the
  `withSpotifyCache` fallback — zero frontend change). Best-effort `artist_bio_cache`
  TTL ledger (migration `20260629_v4_1_artist_bio_cache.sql`).
- Added daily `enrich-bios` job to `etl_daily.yml`. Added `musicbrainzngs` to requirements.
- **Manual step pending:** apply `db/migrations/20260629_v4_1_artist_bio_cache.sql` in the
  Supabase SQL editor (no migration runner / DATABASE_URL available locally). Feature works
  without it; the table only persists the TTL freshness ledger.

## Env note
- Local pipeline venv: `pipeline/.venv` (Python 3.9, deps installed). Gitignored.
