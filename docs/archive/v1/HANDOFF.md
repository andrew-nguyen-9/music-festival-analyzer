# Festival Analyzer — Frontend Handoff

Built overnight while you slept. The full UI is scaffolded, type-checks clean,
and **passes a production build** (`next build` ✓). It's wired for live Supabase
and degrades gracefully with no keys — so it runs *today*, and goes fully live
the moment you paste your URL + anon key.

---

## 🔑 To go live (≈5 minutes, in the morning)

1. **Apply the database** — open the Supabase SQL editor, paste & run:
   `db/setup_supabase.sql` (this is `schema.sql` + a runnable Lollapalooza
   2026 seed with lineups, in one file. Idempotent — safe to re-run).

2. **Add your keys** — in `frontend/`:
   ```bash
   cp .env.local.example .env.local
   ```
   Fill in from Supabase → Project Settings → API:
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://YOURPROJECT.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...   # the public "anon" key, NOT service_role
   ```

3. **Run it**:
   ```bash
   cd frontend
   npm install      # already done once in the workspace; re-run on your machine
   npm run dev      # http://localhost:3000
   ```

You should see Lollapalooza on the index, a themed festival page at
`/festival/lollapalooza`, and artist pages at e.g. `/artist/hozier`.

> ⚠️ Paste only the **anon/public** key here. Never the `service_role` key — it
> bypasses RLS and would be exposed to browsers.

---

## What's built

**3 page templates (all of `UI_SPEC.md`), navigable end-to-end:**

- `/` — `HeroSection` (staggered reveal), `FeaturedFestivals` (horizontal
  scroll), searchable + tag-filterable `FestivalGrid`.
- `/festival/[slug]` — `FestivalHero`, `LineupGrid` (grouped by stage,
  headliners emphasized), `MediaGallery`, `SocialFeed` (IG/X tabs),
  `FunFactsWidget` (auto-advancing carousel), `RelatedFestivals`.
- `/artist/[slug]` — `ArtistHero` (with Spotify stats), `StreamingWidget`,
  `FestivalAppearances`.
- `not-found.tsx` for missing slugs.

**Systems:**

- **Runtime festival theming** — `lib/festival-theme.ts` derives a palette from
  each festival's `accent_color`; `<FestivalThemeStyle>` injects CSS variables
  so every festival/artist page is colored to itself.
- **Resilient data layer** — `lib/supabase.ts` + `lib/queries.ts`. Every query
  is empty-safe: no keys / any error → `[]` or `null`, never a crash. All DB
  access lives here (no raw fetches in components, per `CLAUDE.md`).
- **Empty states everywhere** — media/social/fun-facts render intentional empty
  states until the pipeline populates them.
- **Streaming** — `MusicPlayerToggle`: Spotify embeds are live (auth-free
  iframes); Apple Music is gated behind `NEXT_PUBLIC_APPLE_MUSIC_DEV_TOKEN` and
  shows a clean "coming soon" panel until you add a token.
- **Motion** — baseline fade/stagger via `Reveal`, all respecting
  `prefers-reduced-motion`.

---

## Decisions made while you slept (override any of these)

These are the points I'd have grilled you on; I proceeded on the recommended
answer since you were asleep:

| Decision | Chosen | Why |
|---|---|---|
| Build with no keys yet | Resilient client + empty states; `force-dynamic` pages | You picked "live Supabase," but keys come in the morning. This builds now, live later — zero rework. |
| Empty-data look | Accent-gradient placeholders + first-class empty states | No media/social/facts rows yet; pages still look designed. |
| Seed scope | Included **lineup rows** (festival↔artist links) so nav works; left media/social/facts empty | Reconciles "skip seed depth" with "navigable, no dangling links." |
| Fonts | Inter via runtime `<link>` (not `next/font`) | Removes a build-time network dependency; falls back to system-ui offline. |
| Fidelity | Structural v1 (layout, theming, data, light motion) | Per your choice. Heavy scroll choreography (name-scales-to-nav, IntersectionObserver reveals) is the next polish pass. |

---

## Known cleanup (sandbox couldn't delete files in your folder)

The build sandbox can create but **not delete** files in your folder, so a few
artifacts are left in `frontend/` — all gitignored and safe to remove yourself:

- `node_modules/` (~282 MB), `.next/` (partial), `package-lock.json` (keep this one!)
- `install.log`, `build.log`, `build2.log`, `_wtest.txt` — delete these
- Stray empty dir `festival-analyzer/{docs,scripts,pipeline,frontend,db}` —
  a leftover from an earlier botched `mkdir`; delete it.

```bash
cd "festival-analyzer/frontend" && rm -f install.log build.log build2.log _wtest.txt
```

---

## Next polish pass (not done tonight, by design)

- Scroll-driven hero name → sticky-nav scaling.
- `IntersectionObserver` gallery reveal + horizontal-scroll choreography.
- Global artist search via the `search_all` RPC (index search is client-side
  over loaded festivals for now).
- Apple Music MusicKit token wiring.
- Wire the Python pipeline to populate media/social/fun-facts.

---

## Verification evidence

- `npx tsc --noEmit` → **exit 0** (clean).
- `npx next build` → **✓ Compiled successfully**, types + lint pass, 4/4 routes
  generated (`/`, `/_not-found`, `/artist/[slug]`, `/festival/[slug]`).
