# UI Specification — Festival Analyzer

## Design Philosophy

The UI takes cues from two Awwwards references:
- **thefirstthelast**: Full-bleed editorial imagery, large display type, horizontal scroll sections, deep contrast
- **F1 Evolution**: Data-driven storytelling, scroll-triggered reveals, timeline layout, strong typographic hierarchy

The goal: every festival page feels like it was designed specifically for that festival. Not a template. A destination.

---

## Typography Scale

| Token | Size | Weight | Use |
|-------|------|--------|-----|
| `display-xl` | 96–120px | 800 | Festival name hero |
| `display-lg` | 64–80px | 700 | Section headers |
| `display-md` | 40–48px | 600 | Artist names on cards |
| `heading` | 24–32px | 600 | Stage names, widget headers |
| `body-lg` | 18px | 400 | Festival descriptions |
| `body` | 16px | 400 | Artist bios, metadata |
| `label` | 12–13px | 500 | Tags, dates, metadata labels |

Font stack: `"Inter Variable", "SF Pro Display", system-ui`

---

## Color System

Each festival gets a unique `accent_color` (stored in DB). The system uses this to generate a festival-specific palette at runtime:

```ts
// lib/festival-theme.ts
export function getFestivalTheme(accentHex: string) {
  return {
    accent: accentHex,
    accentLight: lighten(accentHex, 0.3),
    accentDark: darken(accentHex, 0.2),
    surface: '#0A0A0A',       // near-black base (dark-first)
    surfaceElevated: '#141414',
    text: '#FFFFFF',
    textMuted: 'rgba(255,255,255,0.55)',
  };
}
```

**Festival accent colors:**
- Lollapalooza: `#FF4500` (orange-red)
- Coachella: `#00A878` (sage green)
- EDC Vegas: `#FF007F` (hot pink)
- SXSW: `#E63946` (crimson)
- Ultra Miami: `#00D4FF` (electric cyan)
- Governor's Ball: `#7B2FBE` (purple)

---

## Page Templates

### 1. Festival Index (`/`)

**Layout**: Fullscreen hero → horizontal-scroll featured festivals → searchable grid

**Sections:**
- `<HeroSection>` — animated text reveal, "Discover Your Next Festival"
- `<FeaturedFestivals>` — horizontal scroll strip, 6 hero cards with festival photos
- `<SearchBar>` — sticky after hero, with tag filter pills
- `<FestivalGrid>` — masonry or uniform grid, festival cards

**Festival Card props:**
```ts
interface FestivalCardProps {
  name: string;
  city: string;
  state: string;
  dates: string;
  heroImageUrl: string;
  accentColor: string;
  tags: string[];
  slug: string;
}
```

---

### 2. Festival Page (`/festival/[slug]`)

**Layout**: Full-bleed hero → lineup grid → media gallery → social feed → fun facts

**Sections:**
- `<FestivalHero>` — full-viewport Unsplash photo, festival name at display-xl, dates + location
- `<LineupGrid>` — artists grouped by stage/day, with headliner emphasis
- `<MusicToggle>` — Spotify / Apple Music switch, persists to localStorage
- `<MediaGallery>` — masonry Unsplash photo grid
- `<SocialFeed>` — Instagram + X tabs, last 12 posts
- `<FunFactsWidget>` — carousel of AI-generated fun facts
- `<RelatedFestivals>` — tag-matched similar festivals

**Scroll behavior:**
- Festival name scales from display-xl to sticky nav size on scroll
- Lineup sections reveal with Framer Motion staggered fade-in
- Gallery uses `IntersectionObserver` for lazy load

---

### 3. Artist Page (`/artist/[slug]`)

**Layout**: Artist hero photo → bio + genre tags → streaming widget → festivals list

**Sections:**
- `<ArtistHero>` — full-width artist image, name + genre tags
- `<ArtistBio>` — description text
- `<StreamingWidget>` — Spotify embed or Apple Music embed (toggle)
- `<FestivalAppearances>` — all festivals this artist appears in

---

## Component Specs

### `<MusicPlayerToggle>`

```tsx
// Persists user preference in localStorage
// Renders either Spotify or Apple Music embed
interface MusicPlayerToggleProps {
  spotifyId: string | null;
  appleMusicId: string | null;
  previewUrl: string | null;   // fallback 30s Spotify preview
}
```

Toggle UI: pill switch `[🎵 Spotify] [🎵 Apple Music]`  
Falls back to native `<audio>` with `previewUrl` if neither streaming service available.

---

### `<FunFactsWidget>`

```tsx
interface FunFact {
  fact: string;
  category: string;
  artists_mentioned: string[];
}

interface FunFactsWidgetProps {
  facts: FunFact[];
  festivalName: string;
  year: number;
}
```

UI: Card carousel, auto-advances every 6s, category badge (colored by category type), tap to pause.

---

### `<SearchBar>`

Queries Supabase `search_all()` function via debounced API call.  
Filters available: genre tags, festival type, region, season.

```tsx
interface SearchBarProps {
  onResults: (results: SearchResult[]) => void;
  placeholder?: string;
  tags?: string[];
}
```

---

### `<SocialFeed>`

```tsx
interface SocialFeedProps {
  festivalId: string;
  defaultPlatform?: 'instagram' | 'x';
}
```

Pulls from `social_posts` table. Tab switch between platforms.  
Each post card: media thumbnail + caption excerpt + timestamp + like count.

---

## Animations

All animations use Framer Motion. Respect `prefers-reduced-motion`.

| Animation | Trigger | Duration |
|-----------|---------|---------|
| Hero text reveal | Page load | 1.2s stagger |
| Card fade-in | Scroll into view | 0.4s, stagger 0.08s |
| Festival name scale | Scroll | CSS `scale()` tied to `scrollY` |
| Fun facts transition | Auto/tap | 0.3s cross-fade |
| Gallery image reveal | Intersection | 0.5s fade + slight scale |

---

## Responsive Breakpoints

| Breakpoint | Width | Notes |
|------------|-------|-------|
| Mobile | < 640px | Single column, simplified hero |
| Tablet | 640–1024px | 2-col grid, condensed lineup |
| Desktop | 1024–1440px | 3-col grid, full layout |
| Wide | > 1440px | Max-width 1440px centered |

---

## Media Strategy

**Unsplash API** is used for all festival photos. Attribution is required per Unsplash Terms:
- Store `credit_html` field from API response
- Render photographer credit on all photos
- Link to original Unsplash photo URL

Search queries per festival:
- Lollapalooza: `"lollapalooza music festival"`
- Coachella: `"coachella festival crowd"`
- EDC Vegas: `"electric daisy carnival EDC"`
- etc.

Photos are stored as URLs (Unsplash CDN) in the `media` table — no re-hosting required.
