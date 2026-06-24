// ─────────────────────────────────────────────────────────────
// Typed, read-only data-access helpers.
// Components import from here only — no raw Supabase calls in the UI
// (per CLAUDE.md conventions). Every helper is empty-safe: on a missing
// client or any error it returns [] / null and logs a warning, so pages
// always render (with empty states) rather than crash.
// ─────────────────────────────────────────────────────────────

import { getSupabase } from "./supabase";
import { festivalYear } from "./format";
import type {
  Artist,
  ArtistAppearance,
  Festival,
  FunFact,
  FunFactsRow,
  LineupEntry,
  Media,
  SearchResult,
  SocialPost,
} from "./types";

function warn(scope: string, error: unknown): void {
  console.warn(`[queries:${scope}]`, (error as Error)?.message ?? error);
}

// ── Festivals ──────────────────────────────────────────────────

export async function getFestivals(): Promise<Festival[]> {
  const sb = getSupabase();
  if (!sb) return [];
  try {
    const { data, error } = await sb
      .from("festivals")
      .select("*")
      .eq("is_active", true)
      .order("start_date", { ascending: true });
    if (error) throw error;
    return (data as Festival[]) ?? [];
  } catch (e) {
    warn("getFestivals", e);
    return [];
  }
}

export async function getFeaturedFestivals(limit = 6): Promise<Festival[]> {
  const sb = getSupabase();
  if (!sb) return [];
  const today = new Date().toISOString().slice(0, 10);
  try {
    const { data, error } = await sb
      .from("festivals")
      .select("*")
      .eq("is_active", true)
      .contains("tags", ["flagship"])
      .gte("start_date", today)
      .order("start_date", { ascending: true })
      .limit(limit);
    if (error) throw error;
    const featured = (data as Festival[]) ?? [];
    if (featured.length > 0) return featured;
    // Fallback: flagship tag not set yet — return next N upcoming festivals.
    const { data: upcoming, error: e2 } = await sb
      .from("festivals")
      .select("*")
      .eq("is_active", true)
      .gte("start_date", today)
      .order("start_date", { ascending: true })
      .limit(limit);
    if (e2) throw e2;
    return (upcoming as Festival[]) ?? [];
  } catch (e) {
    warn("getFeaturedFestivals", e);
    return [];
  }
}

export async function getFestivalBySlug(
  slug: string,
): Promise<Festival | null> {
  const sb = getSupabase();
  if (!sb) return null;
  try {
    const { data, error } = await sb
      .from("festivals")
      .select("*")
      .eq("slug", slug)
      .maybeSingle();
    if (error) throw error;
    return (data as Festival) ?? null;
  } catch (e) {
    warn("getFestivalBySlug", e);
    return null;
  }
}

export async function getRelatedFestivals(
  festival: Festival,
  limit = 4,
): Promise<Festival[]> {
  const sb = getSupabase();
  if (!sb || !festival.tags?.length) return [];
  try {
    const { data, error } = await sb
      .from("festivals")
      .select("*")
      .neq("id", festival.id)
      .overlaps("tags", festival.tags)
      .limit(limit + 4);
    if (error) throw error;
    const rows = (data as Festival[]) ?? [];
    // Rank by tag-overlap count, desc.
    return rows
      .map((f) => ({
        f,
        score: f.tags.filter((t) => festival.tags.includes(t)).length,
      }))
      .sort((a, b) => b.score - a.score)
      .slice(0, limit)
      .map((x) => x.f);
  } catch (e) {
    warn("getRelatedFestivals", e);
    return [];
  }
}

// ── Lineup (festival × artist) ─────────────────────────────────

export async function getLineup(
  festivalId: string,
  year: number,
): Promise<LineupEntry[]> {
  const sb = getSupabase();
  if (!sb) return [];
  try {
    const { data, error } = await sb
      .from("lineups")
      .select("*, artist:artists(*)")
      .eq("festival_id", festivalId)
      .eq("year", year);
    if (error) throw error;
    return ((data as LineupEntry[]) ?? []).filter((l) => l.artist != null);
  } catch (e) {
    warn("getLineup", e);
    return [];
  }
}

// ── Media ──────────────────────────────────────────────────────

export async function getMedia(
  festivalId: string,
  limit = 18,
): Promise<Media[]> {
  const sb = getSupabase();
  if (!sb) return [];
  try {
    const { data, error } = await sb
      .from("media")
      .select("*")
      .eq("festival_id", festivalId)
      .limit(limit);
    if (error) throw error;
    return (data as Media[]) ?? [];
  } catch (e) {
    warn("getMedia", e);
    return [];
  }
}

// ── Social posts ───────────────────────────────────────────────

export async function getSocialPosts(
  festivalId: string,
  limit = 12,
): Promise<SocialPost[]> {
  const sb = getSupabase();
  if (!sb) return [];
  try {
    const { data, error } = await sb
      .from("social_posts")
      .select("*")
      .eq("festival_id", festivalId)
      .order("posted_at", { ascending: false })
      .limit(limit);
    if (error) throw error;
    return (data as SocialPost[]) ?? [];
  } catch (e) {
    warn("getSocialPosts", e);
    return [];
  }
}

// ── Fun facts ──────────────────────────────────────────────────

export async function getFunFacts(
  festivalId: string,
  year: number,
): Promise<FunFact[]> {
  const sb = getSupabase();
  if (!sb) return [];
  try {
    const { data, error } = await sb
      .from("fun_facts")
      .select("*")
      .eq("festival_id", festivalId)
      .eq("year", year)
      .maybeSingle();
    if (error) throw error;
    const row = data as FunFactsRow | null;
    return Array.isArray(row?.facts) ? row!.facts : [];
  } catch (e) {
    warn("getFunFacts", e);
    return [];
  }
}

// ── Artists ────────────────────────────────────────────────────

export async function getArtistBySlug(slug: string): Promise<Artist | null> {
  const sb = getSupabase();
  if (!sb) return null;
  try {
    const { data, error } = await sb
      .from("artists")
      .select("*")
      .eq("slug", slug)
      .maybeSingle();
    if (error) throw error;
    return (data as Artist) ?? null;
  } catch (e) {
    warn("getArtistBySlug", e);
    return null;
  }
}

export async function getArtistAppearances(
  artistId: string,
): Promise<ArtistAppearance[]> {
  const sb = getSupabase();
  if (!sb) return [];
  try {
    const { data, error } = await sb
      .from("lineups")
      .select("*, festival:festivals(*)")
      .eq("artist_id", artistId)
      .order("year", { ascending: false });
    if (error) throw error;
    return ((data as ArtistAppearance[]) ?? []).filter(
      (a) => a.festival != null,
    );
  } catch (e) {
    warn("getArtistAppearances", e);
    return [];
  }
}

// ── Search (RPC) ───────────────────────────────────────────────

export async function searchAll(query: string): Promise<SearchResult[]> {
  const sb = getSupabase();
  const q = query.trim();
  if (!sb || q.length === 0) return [];
  try {
    const { data, error } = await sb.rpc("search_all", { query: q });
    if (error) throw error;
    return (data as SearchResult[]) ?? [];
  } catch (e) {
    warn("searchAll", e);
    return [];
  }
}

// ── Convenience: festival page bundle ──────────────────────────

export interface FestivalPageData {
  festival: Festival;
  year: number;
  lineup: LineupEntry[];
  media: Media[];
  social: SocialPost[];
  funFacts: FunFact[];
  related: Festival[];
}

export async function getFestivalPageData(
  slug: string,
): Promise<FestivalPageData | null> {
  const festival = await getFestivalBySlug(slug);
  if (!festival) return null;
  const year = festivalYear(festival.start_date);
  const [lineup, media, social, funFacts, related] = await Promise.all([
    getLineup(festival.id, year),
    getMedia(festival.id),
    getSocialPosts(festival.id),
    getFunFacts(festival.id, year),
    getRelatedFestivals(festival),
  ]);
  return { festival, year, lineup, media, social, funFacts, related };
}
