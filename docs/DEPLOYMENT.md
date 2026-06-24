# DEPLOYMENT.md — Vercel (festival.an9.dev)

How Festival Analyzer ships to production. Mechanism: **Vercel Git integration**
(no GitHub deploy workflow, no `VERCEL_TOKEN`). Push to `main` deploys production;
every PR gets an automatic preview URL.

> The repo root **is** the Vercel project root (post-v2.0 flatten). Next.js is
> auto-detected. `vercel.json` only pins the framework; everything else is dashboard config.

---

## 1. Project + Git integration (one-time)

In the Vercel dashboard → the project for **festival.an9.dev**:

1. **Settings → Git** → Connect this GitHub repository.
2. **Settings → Build & Output**
   - Root Directory: `./` (repo root — leave default).
   - Framework Preset: **Next.js** (auto-detected).
   - Build Command / Output: leave default (`next build`).
3. **Settings → Git → Production Branch**: `main`.
4. **Preview Deployments**: leave enabled (default) → every PR gets a preview URL.

## 2. Environment variables

Set in **Settings → Environment Variables**. Apply to **Production** and **Preview**.

| Variable | Scope | Value | Notes |
|----------|-------|-------|-------|
| `NEXT_PUBLIC_SUPABASE_URL` | Public | `https://<project>.supabase.co` | Exposed to the browser by design. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Public | Supabase anon key | Public read-only, enforced by RLS. |

That is **all the runtime needs today.** The frontend reads Supabase with the anon
key only (`lib/supabase.ts`). If env vars are absent the app still builds and renders
empty states — so a misconfigured deploy degrades gracefully instead of crashing.

> **Do NOT** add `SUPABASE_SERVICE_ROLE_KEY` to Vercel yet. It is pipeline-only
> (a GitHub Actions secret). It enters Vercel only in **v2.2**, when a server-side
> Spotify sync function needs it — and then as a **non-`NEXT_PUBLIC_`, server-only**
> variable. Never prefix a secret with `NEXT_PUBLIC_`.

Pipeline/backend secrets (`SUPABASE_SERVICE_ROLE_KEY`, `SPOTIFY_*`, `UNSPLASH_*`,
`ANTHROPIC_API_KEY`) live in **GitHub Actions secrets** for `etl_daily.yml`, not Vercel.
See `pipeline/.env.example`.

## 3. Domain

`festival.an9.dev` (subdomain of the owned `an9.dev`, already connected to Vercel):
**Settings → Domains** → assign `festival.an9.dev` to this project. Vercel issues the TLS cert automatically.

## 4. First production deploy (v2.0.7)

1. Merge `v2` → `main` (after the v2.0 segment gates pass).
2. Vercel auto-builds `main` → production.
3. Confirm the deploy is green in the dashboard and `festival.an9.dev` resolves.
4. **Verify Lollapalooza end-to-end** (see checklist below).

## 5. Live verification checklist

- [ ] `https://festival.an9.dev` loads (home renders festival grid).
- [ ] `/festival/lollapalooza` renders: hero, dates, lineup, schedule.
- [ ] An artist page (`/artist/<slug>`) renders from cached data.
- [ ] No client-side Spotify network calls (DevTools → Network).
- [ ] No console errors; images load from allowed CDNs (`next.config.mjs`).
- [ ] A PR against `main` produced a working preview URL.

## CI relationship

`.github/workflows/ci.yml` typechecks + builds on every PR (secret-free). Vercel's own
build is the deploy gate. CI catches type/build breakage before merge; Vercel ships `main`.
