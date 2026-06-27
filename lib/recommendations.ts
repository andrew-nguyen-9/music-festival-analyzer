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
