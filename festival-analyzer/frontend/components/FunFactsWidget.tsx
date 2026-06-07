"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import EmptyState from "./EmptyState";
import type { FunFact } from "@/lib/types";

interface Props {
  facts: FunFact[];
  festivalName: string;
  year: number;
}

const CATEGORY_HUE: Record<string, string> = {
  history: "#7B2FBE",
  lineup: "#FF4500",
  music: "#00A878",
  trivia: "#00D4FF",
  records: "#E63946",
  default: "#FF7A45",
};

function hueFor(cat: string): string {
  return CATEGORY_HUE[cat?.toLowerCase()] ?? CATEGORY_HUE.default;
}

export default function FunFactsWidget({ facts, festivalName, year }: Props) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const reduce = useReducedMotion();
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const next = useCallback(
    () => setIndex((i) => (i + 1) % Math.max(facts.length, 1)),
    [facts.length],
  );
  const prev = () =>
    setIndex((i) => (i - 1 + facts.length) % Math.max(facts.length, 1));

  useEffect(() => {
    if (paused || facts.length <= 1) return;
    timer.current = setInterval(next, 6000);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [paused, next, facts.length]);

  if (facts.length === 0) {
    return (
      <section className="mx-auto max-w-wide px-5 py-16 md:px-8">
        <h2 className="mb-8 text-display-lg text-white">Did you know?</h2>
        <EmptyState
          title="Fun facts coming soon"
          hint="Run pipeline/fun_facts_generator.py to generate AI fun facts for this lineup."
        />
      </section>
    );
  }

  const fact = facts[index];
  const accent = hueFor(fact.category);

  return (
    <section className="mx-auto max-w-wide px-5 py-16 md:px-8">
      <h2 className="mb-8 text-display-lg text-white">Did you know?</h2>
      <div
        className="relative overflow-hidden rounded-3xl border border-white/10 bg-surface-elevated p-8 md:p-12"
        onClick={() => setPaused((p) => !p)}
        role="button"
        tabIndex={0}
        aria-label="Tap to pause or resume fun facts"
      >
        <div
          className="pointer-events-none absolute inset-0 opacity-25"
          style={{
            background: `radial-gradient(80% 120% at 0% 0%, ${accent}, transparent 60%)`,
          }}
          aria-hidden
        />
        <span
          className="relative inline-block rounded-full px-3 py-1 text-label font-bold uppercase tracking-wide text-black"
          style={{ backgroundColor: accent }}
        >
          {fact.category || "Trivia"}
        </span>

        <AnimatePresence mode="wait">
          <motion.p
            key={index}
            initial={reduce ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduce ? undefined : { opacity: 0, y: -8 }}
            transition={{ duration: 0.3 }}
            className="relative mt-6 max-w-3xl text-display-md font-medium leading-tight text-white"
          >
            {fact.fact}
          </motion.p>
        </AnimatePresence>

        <div className="relative mt-8 flex items-center justify-between">
          <p className="text-label text-[color:var(--text-muted)]">
            {festivalName} · {year}
          </p>
          <div className="flex items-center gap-3">
            <NavBtn label="‹" onClick={(e) => { e.stopPropagation(); prev(); }} />
            <span className="text-label tabular-nums text-white/60">
              {index + 1} / {facts.length}
            </span>
            <NavBtn label="›" onClick={(e) => { e.stopPropagation(); next(); }} />
          </div>
        </div>
      </div>
    </section>
  );
}

function NavBtn({
  label,
  onClick,
}: {
  label: string;
  onClick: (e: React.MouseEvent) => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex h-9 w-9 items-center justify-center rounded-full border border-white/20 text-lg text-white transition-colors hover:bg-white/10"
    >
      {label}
    </button>
  );
}
