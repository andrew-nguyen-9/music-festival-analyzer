"use client";

import { useMemo, useState, useRef, useEffect } from "react";
import FestivalCard from "./FestivalCard";
import EmptyState from "./EmptyState";
import type { Festival } from "@/lib/types";

const TAG_CATEGORIES: Record<string, "genre" | "format" | "region" | "season"> = {
  "multi-genre": "genre",
  "electronic":  "genre",
  "hip-hop":     "genre",
  "rock":        "genre",
  "indie":       "genre",
  "edm":         "genre",
  "country":     "genre",
  "jazz":        "genre",
  "r&b":         "genre",
  "blues":       "genre",
  "folk":        "genre",
  "classical":   "genre",
  "latin":       "genre",
  "reggae":      "genre",
  "punk":        "genre",
  "metal":       "genre",
  "outdoor":     "format",
  "camping":     "format",
  "urban":       "format",
  "multi-day":   "format",
  "indoor":      "format",
  "beach":       "format",
  "midwest":     "region",
  "southwest":   "region",
  "southeast":   "region",
  "west-coast":  "region",
  "northeast":   "region",
  "mountain":    "region",
  "south":       "region",
  "plains":      "region",
  "spring":      "season",
  "summer":      "season",
  "fall":        "season",
  "winter":      "season",
};

const CATEGORY_LABELS: Record<string, string> = {
  genre:  "Genre",
  format: "Setting",
  region: "Region",
  season: "Season",
};

// Geographic east→west ordering
const REGION_ORDER = ["northeast", "southeast", "midwest", "mountain", "southwest", "west-coast", "south", "plains"];
// Chronological season ordering
const SEASON_ORDER = ["spring", "summer", "fall", "winter"];

function sortOptions(cat: string, opts: string[]): string[] {
  const order = cat === "region" ? REGION_ORDER : cat === "season" ? SEASON_ORDER : null;
  if (!order) return [...opts].sort();
  return [...opts].sort((a, b) => {
    const ai = order.indexOf(a);
    const bi = order.indexOf(b);
    if (ai === -1 && bi === -1) return a.localeCompare(b);
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });
}

interface Filters {
  genre:  string | null;
  format: string | null;
  region: string | null;
  season: string | null;
}

interface Props {
  festivals: Festival[];
}

export default function FestivalGrid({ festivals }: Props) {
  const [query, setQuery]   = useState("");
  const [filters, setFilters] = useState<Filters>({ genre: null, format: null, region: null, season: null });

  const tagsByCategory = useMemo(() => {
    const cats: Record<string, Set<string>> = { genre: new Set(), format: new Set(), region: new Set(), season: new Set() };
    for (const f of festivals) {
      for (const t of f.tags ?? []) {
        const cat = TAG_CATEGORIES[t];
        if (cat) cats[cat].add(t);
      }
    }
    return Object.fromEntries(
      Object.entries(cats).map(([k, v]) => [k, sortOptions(k, [...v])])
    ) as Record<string, string[]>;
  }, [festivals]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return festivals.filter((f) => {
      const tags = f.tags ?? [];
      if (filters.genre  && !tags.includes(filters.genre))  return false;
      if (filters.format && !tags.includes(filters.format)) return false;
      if (filters.region && !tags.includes(filters.region)) return false;
      if (filters.season && !tags.includes(filters.season)) return false;
      if (q) {
        return (
          f.name.toLowerCase().includes(q) ||
          (f.city ?? "").toLowerCase().includes(q) ||
          (f.state ?? "").toLowerCase().includes(q) ||
          tags.some((t) => t.toLowerCase().includes(q))
        );
      }
      return true;
    });
  }, [festivals, query, filters]);

  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const sixMonthsAgo = useMemo(() => {
    const d = new Date();
    d.setMonth(d.getMonth() - 6);
    return d.toISOString().slice(0, 10);
  }, []);

  const upcoming = useMemo(
    () => filtered.filter((f) => !f.end_date || f.end_date >= today),
    [filtered, today],
  );
  const recentPast = useMemo(
    () => filtered.filter((f) => f.end_date && f.end_date < today && f.end_date >= sixMonthsAgo),
    [filtered, today, sixMonthsAgo],
  );

  const totalCount = upcoming.length + recentPast.length;
  const activeCount = Object.values(filters).filter(Boolean).length;

  function clearFilters() {
    setFilters({ genre: null, format: null, region: null, season: null });
    setQuery("");
  }

  return (
    <section className="mx-auto max-w-wide px-5 py-10 md:px-8">
      {/* Sticky search + filter bar */}
      <div className="sticky top-16 z-30 -mx-5 mb-8 bg-surface/80 px-5 py-4 backdrop-blur md:-mx-8 md:px-8">
        <div className="flex flex-col gap-3">
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

          <div className="flex flex-wrap items-center gap-2">
            {(["genre", "region", "format", "season"] as const).map((cat) => {
              const options = tagsByCategory[cat] ?? [];
              if (options.length === 0) return null;
              return (
                <CategoryDropdown
                  key={cat}
                  label={CATEGORY_LABELS[cat]}
                  options={options}
                  value={filters[cat]}
                  onChange={(v) => setFilters((prev) => ({ ...prev, [cat]: v }))}
                />
              );
            })}

            {activeCount > 0 && (
              <button
                onClick={clearFilters}
                className="ml-1 rounded-full border border-white/20 px-3.5 py-1.5 text-label text-white/60 transition-colors hover:border-white/40 hover:text-white"
              >
                Clear {activeCount} filter{activeCount > 1 ? "s" : ""}
              </button>
            )}

            <span className="ml-auto text-label text-white/40">
              {totalCount} festival{totalCount !== 1 ? "s" : ""}
            </span>
          </div>
        </div>
      </div>

      {festivals.length === 0 ? (
        <EmptyState
          title="No festivals loaded yet"
          hint="Add your Supabase URL + anon key (.env.local) and run the seed SQL — festivals will appear here automatically."
        />
      ) : totalCount === 0 ? (
        <EmptyState
          title="No matches"
          hint="Try a different search term or clear the active filters."
        />
      ) : (
        <>
          {upcoming.length > 0 && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {upcoming.map((f, i) => (
                <FestivalCard key={f.id} festival={f} priority={i < 3} />
              ))}
            </div>
          )}

          {recentPast.length > 0 && (
            <div className="mt-12">
              <div className="mb-6 flex items-center gap-4">
                <div className="h-px flex-1 bg-white/10" />
                <span className="shrink-0 text-label uppercase tracking-widest text-white/30">Past Events</span>
                <div className="h-px flex-1 bg-white/10" />
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {recentPast.map((f) => (
                  <div
                    key={f.id}
                    className="opacity-50 grayscale transition-all duration-300 hover:opacity-75 hover:grayscale-0"
                  >
                    <FestivalCard festival={f} priority={false} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}

// ── CategoryDropdown ─────────────────────────────────────────────

interface DropdownProps {
  label:    string;
  options:  string[];
  value:    string | null;
  onChange: (v: string | null) => void;
}

function CategoryDropdown({ label, options, value, onChange }: DropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const active = value !== null;
  const displayLabel = active ? formatTag(value!) : label;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className={
          "flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-label uppercase tracking-wide transition-colors " +
          (active
            ? "border-accent bg-accent text-black"
            : "border-white/15 text-white/70 hover:border-white/40 hover:text-white")
        }
      >
        {displayLabel}
        <ChevronIcon open={open} active={active} />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1.5 min-w-[160px] overflow-hidden rounded-xl border border-white/15 bg-surface-elevated shadow-xl">
          <button
            onClick={() => { onChange(null); setOpen(false); }}
            className={
              "w-full px-4 py-2.5 text-left text-label uppercase tracking-wide transition-colors " +
              (!active ? "bg-white/10 text-white" : "text-white/60 hover:bg-white/5 hover:text-white")
            }
          >
            All {label}s
          </button>
          <div className="h-px bg-white/10" />
          {options.map((opt) => (
            <button
              key={opt}
              onClick={() => { onChange(opt === value ? null : opt); setOpen(false); }}
              className={
                "w-full px-4 py-2.5 text-left text-label uppercase tracking-wide transition-colors " +
                (opt === value ? "bg-accent/20 text-accent" : "text-white/70 hover:bg-white/5 hover:text-white")
              }
            >
              {formatTag(opt)}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function formatTag(tag: string) {
  return tag.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function ChevronIcon({ open, active }: { open: boolean; active: boolean }) {
  return (
    <svg
      width="12" height="12"
      viewBox="0 0 12 12"
      className={
        "transition-transform duration-200 " +
        (open ? "rotate-180 " : "") +
        (active ? "text-black" : "text-white/50")
      }
      fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"
    >
      <path d="M2.5 4.5 6 8l3.5-3.5" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg
      className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-white/40"
      width="18" height="18"
      viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
    >
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3-3" />
    </svg>
  );
}
