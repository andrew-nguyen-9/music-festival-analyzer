"use client";

import Image from "next/image";
import { motion, useReducedMotion } from "framer-motion";

const WORDS = ["Discover", "Your", "Next", "Festival"];

const HERO_IMAGE =
  "https://images.unsplash.com/photo-1656401992374-5ce15b9a11fa?q=80&w=2070&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D";

/**
 * Index hero — full-bleed background photo + large editorial display type
 * with a staggered word reveal on load. Reduced-motion friendly.
 */
export default function HeroSection() {
  const reduce = useReducedMotion();
  return (
    <section className="relative flex min-h-[92vh] flex-col justify-end overflow-hidden pb-16 pt-32">
      {/* Full-bleed background photo */}
      <Image
        src={HERO_IMAGE}
        alt=""
        fill
        priority
        sizes="100vw"
        className="-z-20 object-cover"
      />
      {/* Legibility scrim + accent tint */}
      <div className="hero-scrim absolute inset-0 -z-10" aria-hidden />
      <div
        className="pointer-events-none absolute inset-0 -z-10 opacity-60"
        style={{
          background:
            "radial-gradient(70% 80% at 78% 8%, rgba(255,69,0,0.25), transparent 60%), radial-gradient(55% 60% at 8% 95%, rgba(123,47,190,0.20), transparent 60%)",
        }}
        aria-hidden
      />

      {/* Content constrained to max-w-wide, matching all other page sections */}
      <div className="over-media mx-auto w-full max-w-wide px-5 md:px-8">
        <p className="mb-5 text-label uppercase tracking-[0.22em] text-white/80">
          US Music Festivals · Lineup Intelligence
        </p>
        <h1 className="max-w-[14ch] text-display-xl text-white drop-shadow-[0_2px_24px_rgba(0,0,0,0.45)]">
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
        <p className="mt-6 max-w-xl text-body-lg text-white/85 drop-shadow-[0_1px_12px_rgba(0,0,0,0.5)]">
          Every lineup, artist, and moment — from Lollapalooza to 200+ festivals
          across the country. Search by artist, genre, city, or vibe.
        </p>
      </div>
    </section>
  );
}
