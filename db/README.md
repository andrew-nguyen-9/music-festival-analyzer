# Database — Festival Analyzer

Canonical schema: [`schema.sql`](./schema.sql). Apply incremental changes via
timestamped, additive, reversible files in [`migrations/`](./migrations/) — never
hand-edit live tables. One-shot bootstrap (schema + Lolla seed): `setup_supabase.sql`.

> **Access model:** frontend uses the **anon** key (public reads only, enforced by
> RLS). All writes go through the **service-role** key (pipeline / server only).
> Never expose the service-role key to the client or prefix it `NEXT_PUBLIC_`.

## Tables

| Table | Purpose | Key columns | Notes |
|-------|---------|-------------|-------|
| `festivals` | One row per festival | `slug` (unique), `name`, `start_date`/`end_date`, `tags[]`, `accent_color`, `dates_estimated`, `vector_art` | Theming via `accent_color`; `dates_estimated` flags unconfirmed dates. |
| `artists` | One row per artist | `slug` (unique), `spotify_id` (unique), `spotify_popularity`, `genres[]` | Spotify scalars are populated by the pipeline; cache staging in `artist_spotify_cache`. |
| `lineups` | festival × artist join | FK `festival_id`, `artist_id`; `year`; unique `(festival_id, artist_id, year)` | `day` + `set_time_*` drive the schedule views. |
| `media` | Festival photos (Unsplash) | FK `festival_id`, `credit_html` | `credit_html` is the required Unsplash attribution. |
| `social_posts` | IG/X posts per festival | FK `festival_id`, `platform`, unique `(platform, post_id)` | `platform` checked in (`instagram`,`x`). |
| `fun_facts` | AI facts per festival×year | FK `festival_id`, `facts jsonb`, unique `(festival_id, year)` | `facts` = array of `{fact, category}`. |
| `tags` | Normalized tag registry | `slug` (unique), `type` | `type` ∈ genre/vibe/format/region/season. |
| `artist_spotify_cache` | Cached Spotify data (TTL) | FK `artist_id` (unique), `fetched_at`, `ttl_seconds`, `expires_at` (trigger-maintained) | Backing store for v2.2; frontend reads cache, never calls Spotify. |

**View:** `v_upcoming_festivals` — active festivals from the last 30 days onward, for dashboard use.

## Indexes (hot paths)

- Slug lookups (`festivals.slug`, `artists.slug`) and `artists.spotify_id` — covered by **unique constraints** (implicit btree), no extra index needed.
- `idx_lineups_festival (festival_id, year)`, `idx_lineups_artist (artist_id)` — lineup joins both directions.
- `idx_festivals_active_start (is_active, start_date)` — home / featured listing path.
- `idx_artists_popularity (spotify_popularity desc nulls last)` — popularity sort.
- GIN: name trigram (fuzzy search), `tags`, `genres`. Partial: `idx_festivals_dates_estimated`.
- `idx_artist_spotify_cache_expires (expires_at)` — stale-row sweeps.

## RLS

Every table has RLS **enabled** with a single `select using (true)` public-read policy
and **no** insert/update/delete policy, so anon writes are rejected (`42501`). Verified
live: anon read OK on all tables; anon write denied. Service-role bypasses RLS for pipeline writes.

## Live audit snapshot (2026-06-24)

Introspected via the PostgREST OpenAPI endpoint (`/rest/v1/`). Schema reconciled to live;
`schema.sql` had been missing `festivals.dates_estimated`, `festivals.vector_art`, and the
`v_upcoming_festivals` view (added by migration `20260610`) — now reflected.

Row counts: festivals 77 · artists 672 · lineups 851 · tags 22 · media/social_posts/fun_facts 0.
