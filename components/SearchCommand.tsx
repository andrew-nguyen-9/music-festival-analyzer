"use client";

// ⌘K / ctrl-K command palette — cross-festival + artist search (v3.3).
// Debounced fetch to /api/search; keyboard-driven; empty, loading, zero-result
// ("did you mean?") states. Reads no Supabase directly — the API route does.
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { SearchResult, Suggestion } from "@/lib/types";

interface Payload {
  query: string;
  results: SearchResult[];
  suggestions: Suggestion[];
}

const hrefFor = (type: string, slug: string) =>
  type === "festival" ? `/festival/${slug}` : `/artist/${slug}`;

export default function SearchCommand() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [data, setData] = useState<Payload | null>(null);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Global ⌘K / ctrl-K to open, Esc to close.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 0);
    else {
      setQ("");
      setData(null);
      setActive(0);
    }
  }, [open]);

  // Debounced search.
  useEffect(() => {
    const term = q.trim();
    if (term.length < 2) {
      setData(null);
      return;
    }
    setLoading(true);
    const t = setTimeout(async () => {
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(term)}`);
        setData((await res.json()) as Payload);
        setActive(0);
      } catch {
        setData({ query: term, results: [], suggestions: [] });
      } finally {
        setLoading(false);
      }
    }, 180);
    return () => clearTimeout(t);
  }, [q]);

  const go = useCallback(
    (type: string, slug: string) => {
      setOpen(false);
      router.push(hrefFor(type, slug));
    },
    [router],
  );

  const results = data?.results ?? [];
  const onInputKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && results[active]) {
      go(results[active].type, results[active].slug);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Search festivals and artists"
        className="flex items-center gap-2 rounded-full border border-white/15 px-3 py-1.5 text-label uppercase tracking-[0.12em] text-[color:var(--text-muted)] transition-colors hover:text-white"
      >
        <span aria-hidden>⌕</span>
        <span className="hidden sm:inline">Search</span>
        <kbd className="hidden rounded bg-white/10 px-1.5 py-0.5 text-[10px] md:inline">⌘K</kbd>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-[100] flex items-start justify-center bg-black/70 px-4 pt-[12vh] backdrop-blur-sm"
          onClick={() => setOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Search"
        >
          <div
            className="w-full max-w-xl overflow-hidden rounded-2xl border border-white/10 bg-[color:var(--surface,#111)] shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <input
              ref={inputRef}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={onInputKey}
              placeholder="Search festivals, artists, cities, genres…"
              className="w-full bg-transparent px-5 py-4 text-lg text-white outline-none placeholder:text-white/40"
            />
            <div className="max-h-[50vh] overflow-y-auto border-t border-white/10">
              {loading && <p className="px-5 py-4 text-sm text-white/50">Searching…</p>}

              {!loading && q.trim().length >= 2 && results.length === 0 && (
                <div className="px-5 py-4 text-sm text-white/60">
                  <p>No matches for “{q.trim()}”.</p>
                  {(data?.suggestions?.length ?? 0) > 0 && (
                    <p className="mt-2">
                      Did you mean{" "}
                      {data!.suggestions.map((s, i) => (
                        <span key={`${s.type}-${s.slug}`}>
                          {i > 0 && ", "}
                          <button
                            className="text-accent underline-offset-2 hover:underline"
                            onClick={() => go(s.type, s.slug)}
                          >
                            {s.name}
                          </button>
                        </span>
                      ))}
                      ?
                    </p>
                  )}
                </div>
              )}

              {results.map((r, i) => (
                <button
                  key={`${r.type}-${r.id}`}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => go(r.type, r.slug)}
                  className={`flex w-full items-center justify-between px-5 py-3 text-left transition-colors ${
                    i === active ? "bg-white/10" : "hover:bg-white/5"
                  }`}
                >
                  <span className="truncate text-white">{r.name}</span>
                  <span className="ml-3 shrink-0 text-[10px] uppercase tracking-[0.14em] text-white/40">
                    {r.type}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
