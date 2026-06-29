# API Reference

All external APIs used in the Soundcheck pipeline and frontend.

---

## Spotify Web API

**Purpose**: Artist metadata, genres, follower count, popularity score, images  
**Auth**: Client Credentials flow (server-side only; no user login for public data)  
**Free tier**: 1,000 req/day per app  
**Docs**: https://developer.spotify.com/documentation/web-api

> **Server-only.** Spotify is called exclusively by the pipeline sync worker
> (`pipeline/spotify_sync.py`, v2.2), which writes to `artist_spotify_cache`. The
> frontend reads that cache and **never** calls the Spotify Web API. The artist
> page's Spotify *embed* iframe (`open.spotify.com/embed/...`) is an auth-free
> public widget — not a Web API call — and is the sanctioned way to play audio.

### Setup
1. Create app at https://developer.spotify.com/dashboard
2. Copy `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` to `pipeline/.env`
   (and to GitHub Actions secrets for `etl_daily.yml`).

### 2026 API constraints (the worker is built around these)
- **No bulk metadata endpoints** → artists are fetched **individually** via search.
- **Legacy `/artists/{id}/top-tracks` removed** → no server-side preview URLs;
  `preview_url` / `top_tracks` stay null and the embed handles playback.
- **Global `/search` capped at 10 items/request** → the worker pages with `offset`
  (up to `SEARCH_PAGES` pages) so lesser-known acts still get matched.
- **Development Mode tightened** → client-credentials still serves public data.

### Key endpoint used

```
GET /search?q={name}&type=artist&limit=10&offset={0,10,20}
```

One `/search` per artist suffices — the individual `/artists/{id}` endpoint
returns the same fields. In practice 2026 client-credentials responses are
**inconsistent**: `image_url` and the Spotify ID come through reliably, but
`popularity` / `followers` / `genres` are frequently null. The worker therefore
*coalesces forward* (a fresh null never overwrites a known-good cached value),
and the frontend falls back to the artists-table (enricher) values for any field
the cache lacks.

### Name matching
Festival artist names → Spotify IDs via a normalized fuzzy ratio (stdlib
`difflib`); a match is written only above `MATCH_THRESHOLD` (0.85). Target: ≥90%
of artists matched. Unmatched names cache a "miss" row so the worker doesn't
re-search them until the TTL expires; the page falls back to artists-table data.

### Rate limits
- 429 responses include a `Retry-After` header.
- The worker uses `tenacity` backoff that **honors `Retry-After`** on 429 and
  falls back to capped exponential backoff on 5xx (`pipeline/spotify_sync.py`).

---

## Apple Music API (MusicKit JS)

**Purpose**: Artist metadata, Apple Music links, embedded player in frontend  
**Auth**: JWT signed with Apple Developer key (ES256)  
**Free tier**: No rate limits listed; reasonable use expected  
**Docs**: https://developer.apple.com/documentation/applemusicapi

### Setup
1. Apple Developer account required
2. Create a MusicKit identifier at https://developer.apple.com/account
3. Generate a private key (`.p8` file)
4. Set `APPLE_MUSIC_KEY_ID`, `APPLE_MUSIC_TEAM_ID`, `APPLE_MUSIC_PRIVATE_KEY` in `.env`

### JWT generation (Python)
```python
import jwt, time
from pathlib import Path

def generate_apple_music_token() -> str:
    private_key = os.environ["APPLE_MUSIC_PRIVATE_KEY"]  # full PEM string
    return jwt.encode(
        payload={
            "iss": os.environ["APPLE_MUSIC_TEAM_ID"],
            "iat": int(time.time()),
            "exp": int(time.time()) + 15777000,  # 6 months
        },
        key=private_key,
        algorithm="ES256",
        headers={"kid": os.environ["APPLE_MUSIC_KEY_ID"]},
    )
```

### Frontend (MusicKit JS)
```html
<!-- Load once in layout.tsx -->
<script src="https://js-cdn.music.apple.com/musickit/v3/musickit.js"></script>
```

```ts
// lib/applemusic.ts
export async function initMusicKit(developerToken: string) {
  await MusicKit.configure({
    developerToken,
    app: { name: 'Soundcheck', build: '1.0' },
  });
  return MusicKit.getInstance();
}
```

---

## Unsplash API

**Purpose**: High-quality festival photography (free, licensed for use)  
**Auth**: Access Key in query param or `Authorization: Client-ID {key}` header  
**Free tier**: 50 requests/hour  
**Docs**: https://unsplash.com/documentation

### Setup
1. Create app at https://unsplash.com/developers
2. Copy `UNSPLASH_ACCESS_KEY` to `.env`

### Key endpoint
```
GET /search/photos?query=lollapalooza+festival&per_page=20&orientation=landscape
```

### Attribution requirement
Unsplash requires attribution. Store and render `credit_html` from every response:
```json
{
  "user": {
    "name": "Photographer Name",
    "links": { "html": "https://unsplash.com/@username" }
  },
  "links": { "html": "https://unsplash.com/photos/abc123" }
}
```
Render as: `Photo by [Photographer Name](link) on [Unsplash](link)`

---

## Instagram Basic Display API

**Purpose**: Latest posts from each festival's official Instagram  
**Auth**: OAuth 2.0 (requires a Facebook Developer app + Business account access)  
**Free tier**: Yes  
**Docs**: https://developers.facebook.com/docs/instagram-basic-display-api

### Notes
- Requires each festival's Instagram account to authorize the app (or use a proxy service)
- Alternative: use Instagram oEmbed for public posts without auth — simpler but limited
- For Phase 1, use oEmbed for the 6 flagship festivals (public accounts)

### oEmbed (no auth needed for public posts)
```
GET https://graph.facebook.com/v19.0/instagram_oembed?url={POST_URL}&access_token={TOKEN}
```

---

## X (Twitter) API v2

**Purpose**: Latest tweets from each festival's official X account  
**Auth**: Bearer Token  
**Free tier**: Limited — 500k tweets read/month on Basic ($100/mo)  
**Free workaround**: Use Twitter oEmbed for individual tweet display  
**Docs**: https://developer.twitter.com/en/docs/twitter-api

### Strategy for Phase 1 (low cost)
- Cache last 12 posts per festival in `social_posts` table, refresh daily
- Use Bearer Token with Basic tier ($100/mo) OR use Twitter oEmbed for public posts
- If budget is zero: scrape X page via `nitter` proxy (self-hosted, no API needed)

### Key endpoint (if using API)
```
GET /2/users/by/username/{username}          → get user ID
GET /2/users/{id}/tweets?max_results=12      → get latest tweets
  &tweet.fields=created_at,public_metrics,attachments
  &media.fields=url,preview_image_url
  &expansions=attachments.media_keys
```

---

## Anthropic Claude API

**Purpose**: Fun facts generation per festival lineup  
**Model**: `claude-sonnet-4-20250514`  
**Auth**: `ANTHROPIC_API_KEY`  
**Cost**: ~$0.003 per fun facts run (1 festival, 8 facts ≈ 1500 output tokens)  
**Docs**: https://docs.anthropic.com

### Usage pattern
```python
import anthropic
client = anthropic.Anthropic()
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1500,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": prompt}]
)
```

---

## Supabase

**Purpose**: Postgres database + auto-generated REST API + object storage  
**Free tier**: 500MB DB, 1GB storage, 2GB bandwidth/month, unlimited API calls  
**Docs**: https://supabase.com/docs

### Key SDKs
- Python: `supabase-py` (pipeline)
- TypeScript: `@supabase/supabase-js` (frontend)

### Auto-generated REST API
Every table and function is accessible via:
```
https://{project}.supabase.co/rest/v1/{table}
```

Authentication via `apikey` header (anon key for public reads, service role for writes).

### Edge Functions (optional future enhancement)
For server-side proxy of Spotify/Apple Music OAuth tokens to keep client secrets safe,
consider Supabase Edge Functions (Deno runtime, deploy from CLI).
