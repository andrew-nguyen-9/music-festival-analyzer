# Festival Analyzer — Documentation

Start here. This index maps the whole `docs/` tree.

## Operating model
- [`WORKFLOW.md`](./WORKFLOW.md) — versioning (`v[p].[s].[t]`), branch model, segment & phase lifecycle gates. **Read first.**
- [`ROADMAP.md`](./ROADMAP.md) — all phases at a glance.
- [`DEPLOYMENT.md`](./DEPLOYMENT.md) — Vercel Git integration, env vars, domain, live verification.

## Planning (per phase)
- [`planning/v3/PLAN.md`](./planning/v3/PLAN.md) — next phase (stub, fleshed out at v3 kickoff).
- [`archive/v2/PLAN.md`](./archive/v2/PLAN.md) — v2 (shipped `v2.0.0`): every segment, its tasks, dependencies, exit criteria. Frozen.

## Design
- [`design/DESIGN_DIRECTION.md`](./design/DESIGN_DIRECTION.md) — v2 redesign brief (investigative-journalism direction); expanded into a full system in segment v2.5.
- `design/UI_SPEC.md` — v1 design spec. **Superseded in v2.5** (will be archived then).

## API
- `api/API_REFERENCE.md` — external API details + setup (Spotify, Supabase, Unsplash, Anthropic, Apple Music, social).

## Brainstorm (idea backlogs)
- `brainstorm/` — per-phase idea/fix/feature backlogs, written at each phase close-out (gate **h**). Seeds the next phase.

## Archive
- `archive/v1/` — frozen v1.0.0 artifacts (old `HANDOFF.md`, `README` notes, root `schema.sql`, architecture SVG, `graphify-out/`). Never edited, never deleted.
- `archive/v[p]/` — each closed phase's consolidated planning docs land here.

---

### Doc rules
- Docs ride with the branch that changes the behavior they describe — no "docs later."
- When a phase closes, its planning docs move to `archive/v[p]/` (WORKFLOW gate **g**).
- Keep this index current when adding or moving a doc.

> Note: some files referenced here (`api/API_REFERENCE.md`, `design/UI_SPEC.md`,
> `archive/v1/*`, `brainstorm/*`) are **moved/created during segment v2.0**, when the
> repo is flattened and docs consolidated. This index describes the target tree.
