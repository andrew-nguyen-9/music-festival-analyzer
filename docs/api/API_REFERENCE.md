# API Reference

All external APIs used in the Festival Analyzer pipeline and frontend.

---

## Spotify Web API

**Purpose**: Artist metadata, genres, follower count, popularity score, 30s preview URLs  
**Auth**: Client Credentials flow (no user login needed for public data)  
**Free tier**: 1,000 req/day per app (sufficient for Phase 1–2)  
**Docs**: https://developer.spotify.com/documentation/web-api

### Setup
1. Create app at https://developer.spotify.com/dashboard
2. Copy `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` to `.env`

### Key endpoints used

```
GET /search?q=artist:{name}&type=artist&limit=1
GET /artists/{id}/top-tracks?market=US
```

### Rate limits
- 429 responses include `Retry-After` header
- `spotipy` handles retry automatically with `spotipy.Spotify(retries=3)`

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
    app: { name: 'Festival Analyzer', build: '1.0' },
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
