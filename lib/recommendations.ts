// ─────────────────────────────────────────────────────────────
// Recommendations read helpers (v3.6). Neighbours are precomputed nightly by
// pipeline/recommend.py into artist_neighbors; here we just read them. Empty-safe
// like queries.ts: no client / any error → [] so pages still render.
// ─────────────────────────────────────────────────────────────
import { getSupabase } from "./supabase";

export interface SimilarArtist {
  slug: string;
  name: string;
  image_url: string | null;
  genres: string[];
  score: number;
  reason: string | null;
}

/** Top similar artists for an artist, best score first (v3.6). */
export async function getSimilarArtists(
  artistId: string,
  limit = 8,
): Promise<SimilarArtist[]> {
  const sb = getSupabase();
  if (!sb) return [];
  try {
    const { data, error } = await sb
      .from("artist_neighbors")
      .select(
        "score, reason, neighbor:artists!artist_neighbors_neighbor_id_fkey(slug, name, image_url, genres)",
      )
      .eq("artist_id", artistId)
      .order("score", { ascending: false })
      .limit(limit);
    if (error) throw error;
    type Row = {
      score: number;
      reason: string | null;
      // PostgREST embeds type as an array even for a to-one FK.
      neighbor: { slug: string; name: string; image_url: string | null; genres: string[] | null }[] | { slug: string; name: string; image_url: string | null; genres: string[] | null } | null;
    };
    return ((data ?? []) as unknown as Row[]).flatMap((r) => {
      const n = Array.isArray(r.neighbor) ? r.neighbor[0] : r.neighbor;
      if (!n) return [];
      return [{
        slug: n.slug,
        name: n.name,
        image_url: n.image_url,
        genres: n.genres ?? [],
        score: r.score,
        reason: r.reason,
      }];
    });
  } catch (e) {
    console.warn("[recommendations:getSimilarArtists]", (e as Error)?.message ?? e);
    return [];
  }
}

type NeighborRow = {
  neighbor_id: string;
  score: number;
  reason: string | null;
  neighbor:
    | { slug: string; name: string; image_url: string | null; genres: string[] | null }[]
    | { slug: string; name: string; image_url: string | null; genres: string[] | null }
    | null;
};

/**
 * "For you" recommendations from a set of seed artists (e.g. the user's local
 * favourites): aggregate neighbours across seeds, sum scores so an artist liked
 * by several seeds ranks higher, exclude the seeds themselves (v3.7).
 */
export async function getRecommendedArtists(
  seedIds: string[],
  limit = 12,
): Promise<SimilarArtist[]> {
  const sb = getSupabase();
  if (!sb || seedIds.length === 0) return [];
  try {
    // Fetch ALL neighbour rows for the seeds (artist_neighbors keeps ≤ top_k≈20
    // per artist) and aggregate in memory. A global `.order(score).limit()` here
    // would truncate by raw per-row score BEFORE summing, dropping an artist that
    // recurs across many seeds — exactly the cross-seed signal we want to keep.
    const { data, error } = await sb
      .from("artist_neighbors")
      .select(
        "neighbor_id, score, reason, neighbor:artists!artist_neighbors_neighbor_id_fkey(slug, name, image_url, genres)",
      )
      .in("artist_id", seedIds)
      .limit(seedIds.length * 25);
    if (error) throw error;

    const seeds = new Set(seedIds);
    const agg = new Map<string, SimilarArtist>();
    for (const r of (data ?? []) as unknown as NeighborRow[]) {
      if (seeds.has(r.neighbor_id)) continue; // don't recommend what they already like
      const n = Array.isArray(r.neighbor) ? r.neighbor[0] : r.neighbor;
      if (!n) continue;
      const existing = agg.get(r.neighbor_id);
      if (existing) {
        existing.score += r.score;
      } else {
        agg.set(r.neighbor_id, {
          slug: n.slug,
          name: n.name,
          image_url: n.image_url,
          genres: n.genres ?? [],
          score: r.score,
          reason: r.reason,
        });
      }
    }
    return [...agg.values()].sort((a, b) => b.score - a.score).slice(0, limit);
  } catch (e) {
    console.warn("[recommendations:getRecommendedArtists]", (e as Error)?.message ?? e);
    return [];
  }
}
