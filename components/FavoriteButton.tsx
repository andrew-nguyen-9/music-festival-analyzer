"use client";

import { useEffect, useState } from "react";
import {
  isFavorite,
  toggleFavorite,
  subscribeFavorites,
  type Favorite,
} from "@/lib/favorites";

type Props = Omit<Favorite, "savedAt"> & { className?: string };

/**
 * Star/unstar an artist. Persists to IndexedDB (offline-safe, v2.7.3) and
 * reflects changes made elsewhere via the favorites pub/sub.
 */
export default function FavoriteButton({ id, slug, name, className }: Props) {
  const [fav, setFav] = useState(false);

  useEffect(() => {
    let alive = true;
    const refresh = () => isFavorite(id).then((v) => alive && setFav(v));
    refresh();
    const unsub = subscribeFavorites(refresh);
    return () => {
      alive = false;
      unsub();
    };
  }, [id]);

  async function onClick() {
    setFav((v) => !v); // optimistic
    const next = await toggleFavorite({ id, slug, name });
    setFav(next);
  }

  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={fav}
      aria-label={fav ? `Remove ${name} from favorites` : `Save ${name} to favorites`}
      className={
        "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-label font-semibold uppercase tracking-wide transition-colors " +
        (fav
          ? "border-accent bg-accent text-black"
          : "border-white/20 text-white/80 hover:border-white/40 hover:text-white") +
        " " +
        (className ?? "")
      }
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill={fav ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.8" aria-hidden>
        <path d="M12 17.3l-6.16 3.7 1.64-7.03L2 9.24l7.19-.61L12 2l2.81 6.63 7.19.61-5.48 4.73L18.16 21z" />
      </svg>
      {fav ? "Saved" : "Save artist"}
    </button>
  );
}
