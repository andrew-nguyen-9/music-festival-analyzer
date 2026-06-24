// ─────────────────────────────────────────────────────────────
// Typed, read-only data-access helpers.
// Components import from here only — no raw Supabase calls in the UI
// (per CLAUDE.md conventions). Every helper is empty-safe: on a missing
// client or any error it returns [] / null and logs a warning, so pages
// always render (with empty states) rather than crash.
// ─────────────────────────────────────────────────────────────

import { cache } from "react";
import { getSupabase } from "./supabase";
import { festivalYear } from "./format";
import type {
  Artist,
  ArtistAppearance,
  ArtistSpotifyCache,
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

// ─────────────────────────────────────────────────────────────
// Column sets — select only what the UI renders (v2.1.5).
// Derived from actual component field usage; kept here so every query
// shares one source of truth instead of `select("*")`. Rows are cast to the
// full type for ergonomics — only listed columns are present at runtime, and
// components are verified to read only those.
// ─────────────────────────────────────────────────────────────

/** Festival fields a card/list renders (+ filter/ranking keys). */
const FESTIVAL_CARD =
  "id, slug, name, city, state, start_date, end_date, tags, accent_color, hero_image_url, vector_art, dates_estimated, is_active";
/** Festival detail page adds the long-form / secondary fields. */
const FESTIVAL_FULL = `${FESTIVAL_CARD}, country, venue, website_url, description`;

/** Artist fields a lineup card renders — no bio/blobs (851-row join). */
const ARTIST_CARD =
  "id, slug, name, genres, image_url, header_image_url, spotify_popularity, spotify_followers";
/** Artist detail page adds bio, links, preview, origin. */
const ARTIST_FULL =
  "id, slug, name, bio, genres, origin_city, origin_country, website_url, spotify_id, spotify_url, spotify_followers, spotify_popularity, preview_url, image_url, header_image_url";

/** Lineup row columns (excludes unused created_at). */
const LINEUP_COLS =
  "id, festival_id, artist_id, year, stage, day, set_time_start, set_time_end, is_headliner";

// ── Festivals ──────────────────────────────────────────────────

export async function getFestivals(): Promise<Festival[]> {
  const sb = getSupabase();
  if (!sb) return [];
  try {
    const { data, error } = await sb
      .from("festivals")
      .select(FESTIVAL_CARD)
      .eq("is_active", true)
      .order("start_date", { ascending: true });
    if (error) throw error;
    return (data as unknown as Festival[]) ?? [];
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
      .select(FESTIVAL_CARD)
      .eq("is_active", true)
      .contains("tags", ["flagship"])
      .gte("start_date", today)
      .order("start_date", { ascending: true })
      .limit(limit);
    if (error) throw error;
    const featured = (data as unknown as Festival[]) ?? [];
    if (featured.length > 0) return featured;
    // Fallback: flagship tag not set yet — return next N upcoming festivals.
    const { data: upcoming, error: e2 } = await sb
      .from("festivals")
      .select(FESTIVAL_CARD)
      .eq("is_active", true)
      .gte("start_date", today)
      .order("start_date", { ascending: true })
      .limit(limit);
    if (e2) throw e2;
    return (upcoming as unknown as Festival[]) ?? [];
  } catch (e) {
    warn("getFeaturedFestivals", e);
    return [];
  }
}

// Wrapped in React cache() — request-scoped memoization dedupes the double
// fetch from generateMetadata + the page render (same for getArtistBySlug).
export const getFestivalBySlug = cache(async function getFestivalBySlug(
  slug: string,
): Promise<Festival | null> {
  const sb = getSupabase();
  if (!sb) return null;
  try {
    const { data, error } = await sb
      .from("festivals")
      .select(FESTIVAL_FULL)
      .eq("slug", slug)
      .maybeSingle();
    if (error) throw error;
    return (data as unknown as Festival) ?? null;
  } catch (e) {
    warn("getFestivalBySlug", e);
    return null;
  }
});

export async function getRelatedFestivals(
  festival: Festival,
  limit = 4,
): Promise<Festival[]> {
  const sb = getSupabase();
  if (!sb || !festival.tags?.length) return [];
  try {
    const { data, error } = await sb
      .from("festivals")
      .select(FESTIVAL_CARD)
      .neq("id", festival.id)
      .overlaps("tags", festival.tags)
      .limit(limit + 4);
    if (error) throw error;
    const rows = (data as unknown as Festival[]) ?? [];
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
      .select(`${LINEUP_COLS}, artist:artists(${ARTIST_CARD})`)
      .eq("festival_id", festivalId)
      .eq("year", year);
    if (error) throw error;
    return ((data as unknown as LineupEntry[]) ?? []).filter(
      (l) => l.artist != null,
    );
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

export const getArtistBySlug = cache(async function getArtistBySlug(
  slug: string,
): Promise<Artist | null> {
  const sb = getSupabase();
  if (!sb) return null;
  try {
    const { data, error } = await sb
      .from("artists")
      .select(ARTIST_FULL)
      .eq("slug", slug)
      .maybeSingle();
    if (error) throw error;
    return (data as unknown as Artist) ?? null;
  } catch (e) {
    warn("getArtistBySlug", e);
    return null;
  }
});

/** Spotify cache fields the UI overlays onto an artist (v2.2). */
const SPOTIFY_CACHE_COLS =
  "spotify_id, followers, popularity, genres, image_url, preview_url";

/**
 * Cached Spotify data for an artist (v2.2). The frontend reads this table only;
 * it never calls Spotify. Returns null when the sync worker hasn't cached this
 * artist yet (page then falls back to the artists-table values).
 */
export const getArtistSpotifyCache = cache(async function getArtistSpotifyCache(
  artistId: string,
): Promise<ArtistSpotifyCache | null> {
  const sb = getSupabase();
  if (!sb) return null;
  try {
    const { data, error } = await sb
      .from("artist_spotify_cache")
      .select(SPOTIFY_CACHE_COLS)
      .eq("artist_id", artistId)
      .maybeSingle();
    if (error) throw error;
    return (data as unknown as ArtistSpotifyCache) ?? null;
  } catch (e) {
    warn("getArtistSpotifyCache", e);
    return null;
  }
});

/**
 * Overlay cached Spotify fields onto an artist for rendering. Cache wins when a
 * field is present; otherwise the artists-table value (legacy enricher) shows.
 * spotify_url is derived from the cached spotify_id since the cache doesn't
 * store it.
 */
export function withSpotifyCache(
  artist: Artist,
  c: ArtistSpotifyCache | null,
): Artist {
  if (!c) return artist;
  const spotifyId = c.spotify_id ?? artist.spotify_id;
  return {
    ...artist,
    spotify_id: spotifyId,
    spotify_followers: c.followers ?? artist.spotify_followers,
    spotify_popularity: c.popularity ?? artist.spotify_popularity,
    genres: c.genres?.length ? c.genres : artist.genres,
    image_url: c.image_url ?? artist.image_url,
    preview_url: c.preview_url ?? artist.preview_url,
    spotify_url:
      artist.spotify_url ??
      (spotifyId ? `https://open.spotify.com/artist/${spotifyId}` : null),
  };
}

export async function getArtistAppearances(
  artistId: string,
): Promise<ArtistAppearance[]> {
  const sb = getSupabase();
  if (!sb) return [];
  try {
    const { data, error } = await sb
      .from("lineups")
      .select(`${LINEUP_COLS}, festival:festivals(${FESTIVAL_CARD})`)
      .eq("artist_id", artistId)
      .order("year", { ascending: false });
    if (error) throw error;
    return ((data as unknown as ArtistAppearance[]) ?? []).filter(
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
