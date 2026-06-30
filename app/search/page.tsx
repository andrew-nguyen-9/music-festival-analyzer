import Link from "next/link";
import { searchEnhanced, searchSuggest } from "@/lib/queries";

// Server-rendered search results — deep-linkable (/search?q=…) and a no-JS
// fallback for the ⌘K palette (v3.3). force-dynamic: results follow live data.
export const dynamic = "force-dynamic";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const q = (await searchParams).q?.trim() ?? "";
  const results = q.length >= 2 ? await searchEnhanced(q) : [];
  const suggestions = q.length >= 2 && results.length === 0 ? await searchSuggest(q) : [];

  return (
    <main className="mx-auto min-h-screen max-w-wide px-5 pt-28 md:px-8">
      <form action="/search" className="mb-8">
        <input
          name="q"
          defaultValue={q}
          placeholder="Search festivals, artists, cities, genres…"
          className="w-full rounded-2xl border border-white/15 bg-white/5 px-5 py-4 text-lg text-white outline-none placeholder:text-white/40 focus:border-accent"
        />
      </form>

      {q.length < 2 ? (
        <p className="text-white/50">Type at least two characters to search.</p>
      ) : results.length === 0 ? (
        <div className="text-white/60">
          <p>No matches for “{q}”.</p>
          {suggestions.length > 0 && (
            <p className="mt-2">
              Did you mean{" "}
              {suggestions.map((s, i) => (
                <span key={`${s.type}-${s.slug}`}>
                  {i > 0 && ", "}
                  <Link
                    href={s.type === "festival" ? `/festival/${s.slug}` : `/artist/${s.slug}`}
                    className="text-accent hover:underline"
                  >
                    {s.name}
                  </Link>
                </span>
              ))}
              ?
            </p>
          )}
        </div>
      ) : (
        <ul className="divide-y divide-white/10">
          {results.map((r) => (
            <li key={`${r.type}-${r.id}`}>
              <Link
                href={r.type === "festival" ? `/festival/${r.slug}` : `/artist/${r.slug}`}
                className="flex items-center justify-between py-3 text-white transition-colors hover:text-accent"
              >
                <span className="truncate">{r.name}</span>
                <span className="ml-3 shrink-0 text-[10px] uppercase tracking-[0.14em] text-white/40">
                  {r.type}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
