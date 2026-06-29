import type { Metadata } from "next";
import Link from "next/link";
import Reveal from "@/components/Reveal";

export const metadata: Metadata = {
  title: "About",
  description:
    "Soundcheck is an autonomous, data-driven guide to US music festivals — lineups, artists, and the moments that define them.",
};

const SOURCES = [
  { name: "Spotify", role: "Artist metadata, genres, popularity & players" },
  { name: "Unsplash", role: "Festival & city photography" },
  { name: "Claude", role: "AI-generated fun facts per lineup" },
  { name: "Supabase", role: "Postgres data layer + public API" },
];

const PHASES = [
  { n: "01", title: "Lollapalooza", body: "Full build — database, pipeline, and the complete festival experience end to end." },
  { n: "02", title: "Top 6 festivals", body: "Coachella, EDC, SXSW, Ultra, Governors Ball — proving the pipeline scales." },
  { n: "03", title: "All of the US", body: "200+ festivals, fuzzy search at scale, every lineup worth knowing." },
];

export default function AboutPage() {
  return (
    <div className="relative overflow-hidden">
      {/* ambient backdrop */}
      <div
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[70vh]"
        style={{
          background:
            "radial-gradient(60% 60% at 80% 0%, rgba(255,69,0,0.18), transparent 60%), radial-gradient(50% 50% at 0% 20%, rgba(123,47,190,0.16), transparent 60%)",
        }}
        aria-hidden
      />

      {/* Manifesto hero */}
      <section className="mx-auto max-w-wide px-5 pb-12 pt-40 md:px-8">
        <p className="mb-6 text-label uppercase tracking-[0.28em] text-accent">
          About
        </p>
        <h1 className="max-w-[16ch] text-display-xl text-white">
          Lineup intelligence for the live-music obsessed.
        </h1>
        <p className="mt-8 max-w-2xl text-body-lg leading-relaxed text-white/80">
          Soundcheck turns scattered lineup announcements into a single,
          beautiful place to discover who&apos;s playing, what they sound like,
          and why it matters — one festival at a time, designed like each one
          deserves its own destination.
        </p>
      </section>

      {/* Big stat band */}
      <section className="border-y border-white/10 bg-surface-elevated/50">
        <div className="mx-auto grid max-w-wide grid-cols-2 gap-y-8 px-5 py-14 md:grid-cols-4 md:px-8">
          {[
            { k: "200+", v: "Festivals on the roadmap" },
            { k: "1", v: "Live today — Lollapalooza" },
            { k: "100%", v: "Data-driven, no hardcoding" },
            { k: "∞", v: "Genres, cities, and vibes" },
          ].map((s) => (
            <Reveal key={s.v}>
              <p className="text-display-lg text-accent">{s.k}</p>
              <p className="mt-1 text-label uppercase tracking-wide text-white/60">
                {s.v}
              </p>
            </Reveal>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-wide px-5 py-20 md:px-8">
        <Reveal>
          <h2 className="text-display-lg text-white">How it&apos;s built</h2>
        </Reveal>
        <p className="mt-5 max-w-2xl text-body-lg text-white/75">
          An autonomous pipeline scrapes, enriches, and refreshes data daily —
          then a Next.js front end renders a theme generated from each
          festival&apos;s own colors. Every page pulls live from the database;
          nothing is hardcoded.
        </p>
        <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {SOURCES.map((s, i) => (
            <Reveal key={s.name} delay={i * 0.06}>
              <div className="h-full rounded-2xl border border-white/10 bg-surface-elevated p-5">
                <p className="text-heading font-semibold text-white">
                  {s.name}
                </p>
                <p className="mt-2 text-body text-[color:var(--text-muted)]">
                  {s.role}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Roadmap */}
      <section className="mx-auto max-w-wide px-5 py-20 md:px-8">
        <Reveal>
          <h2 className="text-display-lg text-white">The roadmap</h2>
        </Reveal>
        <div className="mt-10 space-y-px overflow-hidden rounded-2xl border border-white/10">
          {PHASES.map((p, i) => (
            <Reveal key={p.n} delay={i * 0.08}>
              <div className="flex flex-col gap-2 bg-surface-elevated p-6 sm:flex-row sm:items-baseline sm:gap-8 md:p-8">
                <span className="text-display-md font-extrabold text-accent">
                  {p.n}
                </span>
                <div>
                  <h3 className="text-heading font-semibold text-white">
                    {p.title}
                  </h3>
                  <p className="mt-1 max-w-xl text-body text-white/70">
                    {p.body}
                  </p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-wide px-5 pb-28 pt-6 md:px-8">
        <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-accent/20 to-transparent p-10 text-center md:p-16">
          <h2 className="text-display-md font-semibold text-white">
            Find your next festival.
          </h2>
          <Link
            href="/"
            className="mt-7 inline-block rounded-full bg-accent px-7 py-3.5 text-label font-semibold uppercase tracking-wide text-black transition-transform hover:scale-105"
          >
            Browse festivals
          </Link>
        </div>
      </section>
    </div>
  );
}
