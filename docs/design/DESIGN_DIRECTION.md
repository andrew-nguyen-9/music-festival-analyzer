# DESIGN_DIRECTION.md — v2 Redesign Brief

> This is the **direction**, not the final system. It briefs segment **v2.5**,
> which expands it into a full design system (tokens, components, motion spec)
> and chooses one visual variant via design exploration. v2.6 then builds it.

---

## The thesis

Festival Analyzer should not look like Spotify, and should not look like a
vibe-coded template (centered hero, three feature cards, gradient buttons). It
should feel like a **piece of investigative journalism** — the kind of
scroll-driven interactive feature the NYT, The Pudding, or an F1-evolution piece
publishes: the interface *tells the story of a festival* and walks the reader
through it.

The user explicitly asked for big creative risk. Take it here.

## What to move away from

- Spotify-clone chrome (green accents, rounded cards, list-of-rows everywhere).
- Generic SaaS landing patterns (hero + 3 cards + CTA).
- Flat, contextless grids where every festival/artist looks identical.

## What to move toward

**Editorial, narrative, dark-by-default.**

- **Story-first layout.** A festival page reads top-to-bottom as a narrative:
  the arrival (full-bleed hero), the cast (lineup as a feature, not a table),
  the map (stages/locations), the data (lineup analysis as data-journalism),
  the artifacts (media/social/fun-facts). Scroll *is* the narrative device.
- **Oversized editorial typography.** Festival name at display scale (80–120px+),
  strong type hierarchy, generous whitespace, real typographic personality —
  not the default system stack.
- **Dark-by-default.** Festivals are night events; a blinding white UI at a
  10pm headliner set is an instant closed tab. Dark is the base theme.
- **Per-festival identity.** Carry the existing runtime accent-color theming
  forward, but push it further — each festival should feel like its own
  published feature, not a reskinned card.
- **Data as narrative.** Lineup analysis, popularity, genre spread rendered as
  scrollytelling data viz (timelines, charts that reveal on scroll), the way an
  investigative piece visualizes its evidence.
- **Artist-as-feature.** The artist page (v2.4) frames the artist like a profile
  subject — normalized portrait framing so wildly different source images read
  as one consistent editorial treatment.

## Motion language

- **Scroll-driven reveals** carry the story; reduced-motion users get the same
  content without the choreography.
- **View Transitions API** for native-app morphing: a portrait in the lineup
  grid morphs/expands into the artist-page header (v2.6).
- **Micro-interactions** with intent — audio micro-players (hover/long-press →
  30s preview), subtle state feedback. No clunky iframe widgets slapped around.
- Motion serves the narrative; never decoration for its own sake.

## Reference language (mood, not to copy)

- F1-evolution-since-1950 interactive — data-driven storytelling, timeline layout.
- "First/Last" editorial awwwards site — full-bleed, large type, scroll reveals.
- NYT / The Pudding interactive features — narrative scrollytelling with embedded data viz.

## Constraints the design must respect

- **Offline-first (v2.7):** the design degrades cleanly with cached/partial data;
  empty and offline states are first-class, not afterthoughts.
- **Performance (v2.10):** big type and full-bleed imagery within LCP/CLS/INP
  budgets — image optimization is part of the design, not a fix later.
- **Accessibility:** contrast, focus, and reduced-motion are requirements, not
  polish. Dark-default still meets contrast targets.
- **Theming:** must compose with per-festival `accent_color` runtime theming.

## Deliverables of v2.5 (where this direction goes next)

1. Type scale + chosen typefaces.
2. Color system: dark base + accent-theming rules + contrast-safe tokens.
3. Spacing, grid, and layout primitives.
4. Motion spec (scroll, View Transitions, reduced-motion).
5. Component inventory mapped to the new language.
6. One chosen visual variant (from 2–3 explored via `/frontend-design` / `/design-shotgun` / figma).
7. Supersede the v1 `docs/design/UI_SPEC.md`.
