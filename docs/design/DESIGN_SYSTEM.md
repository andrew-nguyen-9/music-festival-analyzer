# DESIGN_SYSTEM.md — Soundcheck (v2.5)

> The finalized design system for v2. It expands
> [`DESIGN_DIRECTION.md`](./DESIGN_DIRECTION.md) into tokens, rules, and a chosen
> visual direction. **v2.6 applies this; this segment does not rebuild the app.**
> Supersedes [`UI_SPEC.md`](./UI_SPEC.md) (v1 — archived note at its top).

---

## 1. Chosen direction — **"The Dossier"**

One direction was chosen from the exploration: **The Dossier** — the festival page
reads like an investigative editorial dossier on that festival. Dark, type-led,
evidence-forward. Picked over the two alternatives below because it best serves the
DESIGN_DIRECTION thesis (narrative, data-as-evidence) and degrades cleanly to
offline/partial data (v2.7) — the layout is content-driven, not imagery-dependent.

| Variant | Why not |
|---------|---------|
| **A — Poster** (maximal full-bleed imagery, type over photo) | Breaks when imagery is missing/offline; LCP-heavy. |
| **B — Spotify-grid** (familiar card rows) | Explicitly rejected by the brief. |
| **C — The Dossier** ✅ | Narrative + data-forward; works image-light; theming composes cleanly. |

**Feel:** an investigative feature that happens to be interactive. Generous
whitespace, oversized editorial headers, a single accent doing the talking, data
rendered as evidence (timelines, popularity bars), motion that advances the story.

---

## 2. Typography

Faces (already loaded in `app/layout.tsx`):
- **Display / headings:** `Space Grotesk` (`--font-display`) — letter-spacing `-0.02em`.
- **Body / UI:** `Inter` (`--font-inter`).

Scale lives in `tailwind.config.ts` (`fontSize`) — the single source of truth:

| Token | Clamp | Use |
|-------|-------|-----|
| `display-xl` | 3.5→7.5rem | Festival / artist name hero |
| `display-lg` | 2.5→5rem | Section headers ("Lineup", "Listen") |
| `display-md` | 1.75→3rem | Headliner / card names |
| `heading` | 1.25→2rem | Stage names, widget headers |
| `body-lg` | 1.125rem | Descriptions, bios |
| `body` | 1rem | Metadata, secondary text |
| `label` | 0.8125rem | Uppercase tracked labels, tags |

Rule: headings use the display face automatically (`globals.css` `h1–h3`). Labels are
uppercase with `tracking-[0.2em]`. Don't introduce ad-hoc sizes — extend the scale.

---

## 3. Color & theming

Dark-by-default. Base tokens (CSS vars in `globals.css`, palette built by
`lib/festival-theme.ts`):

| Token | Value | Role |
|-------|-------|------|
| `--surface` | `#0A0A0A` | page base |
| `--surface-elevated` | `#141414` | cards, panels |
| `--text` | `#FFFFFF` | primary text |
| `--text-muted` | `rgba(255,255,255,0.55)` | secondary text |
| `--accent` / `-light` / `-dark` | per-festival | identity, CTAs, headers |

**Theming rule:** every festival/artist page is wrapped in `<FestivalThemeStyle>`,
which injects `--accent*` from `festivals.accent_color` via
`getFestivalTheme()`. Components reference `accent` (Tailwind) or `var(--accent)` —
never hardcode a festival color in a component. Foreground on an accent fill uses
`readableOn()` (luma-based black/white). Contrast: body text stays ≥ 4.5:1 on
`--surface`; muted text reserved for non-essential metadata only.

---

## 4. Spacing, grid, layout primitives

- **Page width:** `max-w-wide` (1440px), centered. Gutters `px-5 md:px-8`.
- **Section rhythm:** vertical padding `py-16` (major) / `py-12` (minor).
- **Reading column:** `max-w-3xl` for prose (bios, about).
- **Card grids:** `grid-cols-2 sm:grid-cols-3 lg:grid-cols-4`, gap `gap-3`.
- **Radii:** `rounded-xl` (cards), `rounded-2xl` (panels/embeds), `rounded-full` (pills/CTAs).
- **Borders:** `border-white/10` hairlines on elevated surfaces.
- **Portraits:** always via `<Portrait>` (v2.4) — never a raw `<Image>` in a tile.

Breakpoints: mobile `<640` (1-col), tablet `640–1024` (2–3 col), desktop `1024–1440`
(full), wide `>1440` (centered at 1440).

---

## 5. Motion spec

Tokens in `globals.css` (`--ease-*`, `--dur-*`). One easing vocabulary:
`--ease-out-expo` for entrances/morphs, `--ease-out-soft` for micro-feedback.

| Motion | Trigger | Token | Notes |
|--------|---------|-------|-------|
| Scroll reveal | in-view | `--dur-reveal` + `--ease-out-expo` | fade + 16px rise; staggered (≤0.4s cap) |
| Grid → detail morph | navigation | `--dur-morph` | View Transitions API; `view-transition-name` on the portrait (v2.6) |
| Hover / press | pointer | `--dur-micro` + `--ease-out-soft` | scale 1.02–1.05, never layout-shifting |
| Audio preview | hover / long-press | — | `<PreviewPlayer>` (v2.4) |

**Reduced motion is a hard requirement, not a toggle.** `globals.css` already zeroes
animation/transition durations under `prefers-reduced-motion: reduce`. Reveals must
render their final state with no JS dependency (content first, choreography second).
View Transitions must no-op gracefully under reduced motion.

---

## 6. Component inventory (mapped to the system)

| Component | Role | System notes |
|-----------|------|--------------|
| `FestivalThemeStyle` | injects accent palette | wrap every themed route |
| `Portrait` | normalized media layer | focal default `50% 28%`; the only image primitive for tiles |
| `PreviewPlayer` | 30s audio micro-player | accent-filled pill |
| `Reveal` | scroll-in reveal wrapper | uses reveal token; reduced-motion safe |
| `EmptyState` | "no data yet" panel | first-class, not an afterthought |
| `LineupGrid` / `…ByDay` / `…ByPopularity` | lineup as feature | card grid; headliner emphasis |
| `Nav` / footer | chrome | hairline borders, muted text |
| `FunFactsWidget` / `SocialFeed` / `MediaGallery` | artifacts | the "evidence" tail of the dossier |

New components in later segments (`WallpaperStudio` v2.8, playlist CTA v2.9, offline
indicators v2.7) must consume these tokens — no parallel styling systems.

---

## 7. Constraints carried forward

- **Offline-first (v2.7):** empty/partial/cached states are designed, not patched.
- **Performance (v2.10):** big type + imagery within LCP/CLS/INP budgets; `Portrait`
  uses `next/image` with explicit `sizes`; fonts must not block (v2.10 revisits).
- **Accessibility:** contrast targets above; visible focus; reduced-motion; alt text
  on every `Portrait`.
- **Theming composes** with runtime `accent_color` everywhere.
