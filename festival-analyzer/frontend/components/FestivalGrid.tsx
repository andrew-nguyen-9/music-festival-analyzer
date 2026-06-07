"use client";

import { useMemo, useState } from "react";
import FestivalCard from "./FestivalCard";
import EmptyState from "./EmptyState";
import type { Festival } from "@/lib/types";

interface Props {
  festivals: Festival[];
}

/**
 * Searchable, tag-filterable festival grid. Filters the already-loaded
 * festival set client-side (works fully offline). Sticky search bar.
 */
export default function FestivalGrid({ festivals }: Props) {
  const [query, setQuery] = useState("");
  const [activeTag, setActiveTag] = useState<string | null>(null);

  const allTags = useMemo(() => {
    const counts = new Map<string, number>();
    for (const f of festivals)
      for (const t of f.tags ?? []) counts.set(t, (counts.get(t) ?? 0) + 1);
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([t]) => t);
  }, [festivals]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return festivals.filter((f) => {
      const matchesTag = !activeTag || f.tags?.includes(activeTag);
      const matchesQuery =
        q.length === 0 ||
        f.name.toLowerCase().includes(q) ||
        (f.city ?? "").toLowerCase().includes(q) ||
        (f.state ?? "").toLowerCase().includes(q) ||
        (f.tags ?? []).some((t) => t.toLowerCase().includes(q));
      return matchesTag && matchesQuery;
    });
  }, [festivals, query, activeTag]);

  return (
    <section className="mx-auto max-w-wide px-5 py-10 md:px-8">
      {/* Sticky search + filters */}
      <div className="sticky top-16 z-30 -mx-5 mb-8 bg-surface/80 px-5 py-4 backdrop-blur md:-mx-8 md:px-8">
        <div className="flex flex-col gap-4">
          <div className="relative">
            <SearchIcon />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search festivals by name, city, or tag…"
              className="w-full rounded-full border border-white/15 bg-surface-elevated py-3 pl-11 pr-4 text-body text-white placeholder:text-white/40 outline-none transition-colors focus:border-accent"
            />
          </div>
          {allTags.length > 0 && (
            <div className="no-scrollbar flex gap-2 overflow-x-auto">
              <Pill
                label="All"
                active={activeTag === null}
                onClick={() => setActiveTag(null)}
              />
              {allTags.map((t) => (
                <Pill
                  key={t}
                  label={t}
                  active={activeTag === t}
                  onClick={() => setActiveTag(activeTag === t ? null : t)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {festivals.length === 0 ? (
        <EmptyState
          title="No festivals loaded yet"
          hint="Add your Supabase URL + anon key (.env.local) and run the seed SQL — festivals will appear here automatically."
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No matches"
          hint="Try a different search term or clear the active filter."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((f, i) => (
            <FestivalCard key={f.id} festival={f} priority={i < 3} />
          ))}
        </div>
      )}
    </section>
  );
}

function Pill({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={
        "shrink-0 rounded-full border px-3.5 py-1.5 text-label uppercase tracking-wide transition-colors " +
        (active
          ? "border-accent bg-accent text-black"
          : "border-white/15 text-white/70 hover:border-white/40 hover:text-white")
      }
    >
      {label}
    </button>
  );
}

function SearchIcon() {
  return (
    <svg
      className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-white/40"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
    >
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3-3" />
    </svg>
  );
}
