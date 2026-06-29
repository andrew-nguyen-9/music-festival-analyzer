# WORKFLOW.md — Versioning, Branching & Phase Lifecycle

This is the operating model for all work on Soundcheck from v2 onward.
It is deliberately strict: every change flows through a numbered phase → segment
→ task hierarchy, and every segment and phase has explicit entry and exit gates.

> All work prior to this model is frozen as **v1.0.0** (archived under
> `docs/archive/v1/`, never deleted). The current development line is **v2**.

---

## 1. Version scheme — `v[p].[s].[t]`

```
v [phase] . [segment] . [task]
   │          │           │
   │          │           └─ task: a single unit of work; commit-level, not a branch
   │          └───────────── segment: a coherent slice of the phase; gets a sub-branch
   └──────────────────────── phase: a major version of the product; gets a branch off main
```

| Token | Example | Is a branch? | Meaning |
|-------|---------|--------------|---------|
| Phase `v[p]` | `v2` | **Yes** — cut from `main` | A major version (foundation, redesign, scale…). |
| Segment `v[p].[s]` | `v2.1` | **Yes** — cut from the phase branch | A dependency-ordered slice of the phase. |
| Task `v[p].[s].[t]` | `v2.1.3` | No — a commit inside the segment | The smallest tracked unit of work. |

Segment `0` is always **foundation/restructure** for the phase. Tasks start at
`.1` within a segment (e.g. `v2.1.1` is the first task of segment 1).

### Branch naming

```
Phase branch:    v2
Segment branch:  v2.1-data-layer        (v[p].[s]-kebab-slug)
```

Tasks are **not** branches — they are commits on the segment branch, referenced in
commit messages and the plan (e.g. `v2.1.3: add artist_cache index`).

---

## 2. Segment lifecycle (every `v[p].[s]`)

Each segment is a self-contained, shippable slice. Run these in order:

1. **Cut** the segment sub-branch from the **phase branch** (`git switch v2 && git switch -c v2.1-data-layer`).
2. **Tasks** — implement each task `v2.s.t` in order; commit per task.
3. **Build** — the app builds clean (`next build`, pipeline imports, no type errors).
4. **Test** — unit/integration checks for the segment's logic pass.
5. **QA** — run `/qa` (or `/qa-only` for report-first) against the segment's surface.
6. **Code review** — run `/code-review` (escalate to `ultra` for risky segments).
7. **Commit** — finalize; clean working tree.
8. **Push to parent** — merge the segment branch into the **phase branch** `v2`
   (not `main`), then **delete the segment sub-branch**.

A segment is **done** only when all eight gates pass. A red gate blocks the merge.

### Segment exit criteria (generic)
- Build green, tests green, no `/code-review` blockers open.
- Segment goal in `PLAN.md` met; exit criteria for that segment checked off.
- Docs touched by the segment updated in the same branch.

---

## 3. Phase lifecycle (every `v[p]`)

Open the phase by cutting the phase branch from `main` (`git switch main && git switch -c v2`).
Segments merge into it over time. Close the phase with these gates, in order:

| Gate | Action |
|------|--------|
| **(a)** QA testing | Full-app `/qa` across all segments' surfaces. |
| **(b)** Code review | `/code-review` (prefer `ultra`) over the whole phase diff. |
| **(c)** Commit | Final phase commit; clean tree. |
| **(d)** Merge to main | Merge phase branch `v2` → `main`. |
| **(e)** Delete branches | Delete the phase branch and any leftover sub-branches (`/clean_gone`). |
| **(f)** Review docs | Read every doc; reconcile drift against shipped reality. |
| **(g)** Consolidate + archive | Move the phase's planning docs to `docs/archive/v[p]/`. |
| **(h)** Brainstorm next | Write `docs/brainstorm/v[p+1]-backlog.md` from ideas/fixes/features surfaced during the phase. |

---

## 4. Tooling per gate

| Need | Tool |
|------|------|
| QA a web surface | `/qa`, `/qa-only`, `/browse` |
| Code review | `/code-review` (`ultra` for high-risk) |
| Visual/design QA | `/design-review`, chrome-devtools, playwright |
| Performance / Web Vitals | `/benchmark`, chrome-devtools lighthouse |
| Commit / PR | `/ce-commit`, `/ce-commit-push-pr` |
| Branch cleanup | `/clean_gone`, `/ce-clean-gone-branches` |
| Token efficiency | RTK (auto via hook), caveman + ponytail modes |
| Symbol navigation | graphify (`graphify-out/`), context7 for library docs |

---

## 5. Rules of the model

- **Never commit straight to `main`.** Main only receives merges from a closed phase.
- **Never merge a segment to `main`.** Segments merge to their phase branch.
- **One segment, one concern.** If a segment sprawls, split it into two segments.
- **Docs ride with the branch.** A segment that changes behavior updates its docs in
  the same sub-branch — no "docs later."
- **Secrets never committed.** `.env*` stay local/Vercel; see `CLAUDE.md` → Do Not.
- **Idempotent + reversible.** Pipeline upserts, DB migrations timestamped and additive.
