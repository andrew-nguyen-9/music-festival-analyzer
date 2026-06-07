"use client";

import { motion, useReducedMotion } from "framer-motion";

const WORDS = ["Discover", "Your", "Next", "Festival"];

/**
 * Index hero — large editorial display type with a staggered word reveal
 * on load. Reduced-motion friendly.
 */
export default function HeroSection() {
  const reduce = useReducedMotion();
  return (
    <section className="relative flex min-h-[88vh] flex-col justify-end overflow-hidden px-5 pb-16 pt-32 md:px-8">
      {/* ambient gradient backdrop */}
      <div
        className="pointer-events-none absolute inset-0 -z-10 opacity-70"
        style={{
          background:
            "radial-gradient(60% 80% at 75% 10%, rgba(255,69,0,0.22), transparent 60%), radial-gradient(50% 60% at 10% 90%, rgba(123,47,190,0.18), transparent 60%)",
        }}
        aria-hidden
      />
      <p className="mb-5 text-label uppercase tracking-[0.22em] text-[color:var(--text-muted)]">
        US Music Festivals · Lineup Intelligence
      </p>
      <h1 className="max-w-[14ch] text-display-xl text-white">
        {WORDS.map((w, i) => (
          <motion.span
            key={w}
            className="mr-[0.25em] inline-block"
            initial={reduce ? false : { opacity: 0, y: "0.4em" }}
            animate={reduce ? {} : { opacity: 1, y: 0 }}
            transition={{
              duration: 0.8,
              delay: 0.15 * i,
              ease: [0.22, 1, 0.36, 1],
            }}
          >
            {w === "Festival" ? <span className="text-accent">{w}</span> : w}
          </motion.span>
        ))}
      </h1>
      <p className="mt-6 max-w-xl text-body-lg text-[color:var(--text-muted)]">
        Every lineup, artist, and moment — from Lollapalooza to 200+ festivals
        across the country. Search by artist, genre, city, or vibe.
      </p>
    </section>
  );
}
