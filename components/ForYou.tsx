"use client";

// "For You" home section (v3.7). Personalized from device-local favourites
// (lib/favorites, IndexedDB) — works signed-out, no account required. Posts the
// favourited artist ids to /api/recommendations and renders the aggregate
// neighbours. Renders nothing until there are favourites + recs, so the generic
// home is unchanged for new visitors.
import { useEffect, useState } from "react";
import Link from "next/link";
import { listFavorites, subscribeFavorites } from "@/lib/favorites";
import type { SimilarArtist } from "@/lib/recommendations";

export default function ForYou() {
  const [recs, setRecs] = useState<SimilarArtist[]>([]);
  const [hasFavorites, setHasFavorites] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      const favs = await listFavorites();
      if (cancelled) return;
      setHasFavorites(favs.length > 0);
      if (favs.length === 0) {
        setRecs([]);
        return;
      }
      try {
        const res = await fetch("/api/recommendations", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ artistIds: favs.map((f) => f.id) }),
        });
        const { artists } = (await res.json()) as { artists: SimilarArtist[] };
        if (!cancelled) setRecs(artists ?? []);
      } catch {
        if (!cancelled) setRecs([]);
      }
    };
    refresh();
    const unsub = subscribeFavorites(refresh);
    return () => {
      cancelled = true;
      unsub();
    };
  }, []);

  if (!hasFavorites || recs.length === 0) return null;

  return (
    <section className="mx-auto max-w-wide px-5 py-12 md:px-8">
      <h2 className="mb-2 text-heading font-semibold text-white">For you</h2>
      <p className="mb-8 text-sm text-white/50">
        Based on the {recs.length > 1 ? "artists" : "artist"} you’ve starred.
      </p>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
        {recs.map((a) => (
          <Link
            key={a.slug}
            href={`/artist/${a.slug}`}
            className="group rounded-2xl border border-white/10 bg-white/5 p-4 transition-colors hover:border-accent hover:bg-white/10"
          >
            <span className="block truncate font-medium text-white group-hover:text-accent">
              {a.name}
            </span>
            {a.genres.length > 0 && (
              <span className="mt-1 block truncate text-xs text-white/50">
                {a.genres.slice(0, 2).join(" · ")}
              </span>
            )}
          </Link>
        ))}
      </div>
    </section>
  );
}
