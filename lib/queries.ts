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
  FestivalGuide,
  IngestionRunSummary,
  LineupEntry,
  SearchResult,
  Stage,
  Suggestion,
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

/** Artist fields a lineup card renders — no bio/blobs (851-row join).
 *  preview_url powers the tile hover micro-player (v2.6.4). */
const ARTIST_CARD =
  "id, slug, name, genres, image_url, header_image_url, spotify_popularity, spotify_followers, preview_url";
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
      // Real-data only (v4.5, depends on v4.2): a confirmed (non-estimated) date
      // means the festival was verified from Ticketmaster/official — keeps
      // placeholder/TBA festivals out of the featured carousel.
      .eq("dates_estimated", false)
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

// ── Stages (geocoded; backs the v2.8 wallpaper map) ────────────

export async function getStages(festivalId: string): Promise<Stage[]> {
  const sb = getSupabase();
  if (!sb) return [];
  try {
    const { data, error } = await sb
      .from("stages")
      .select("id, festival_id, name, latitude, longitude, coords_source")
      .eq("festival_id", festivalId);
    if (error) throw error;
    return (data as unknown as Stage[]) ?? [];
  } catch (e) {
    warn("getStages", e);
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

/**
 * Spotify artist ids for the given internal artist ids, from the v2.2 cache.
 * The smart-playlist flow resolves top tracks client-side with the user's PKCE
 * token (the app/client-credentials token is 403'd from /artists/top-tracks),
 * so the server only needs to hand back the matched Spotify ids. Deduped;
 * returns [] when none are matched/cached.
 */
export async function getArtistSpotifyIds(
  artistIds: string[],
): Promise<string[]> {
  const sb = getSupabase();
  if (!sb || artistIds.length === 0) return [];
  try {
    const { data, error } = await sb
      .from("artist_spotify_cache")
      .select("spotify_id")
      .in("artist_id", artistIds)
      .not("spotify_id", "is", null);
    if (error) throw error;
    return Array.from(
      new Set(
        ((data as { spotify_id: string | null }[]) ?? [])
          .map((r) => r.spotify_id)
          .filter((x): x is string => Boolean(x)),
      ),
    );
  } catch (e) {
    warn("getArtistSpotifyIds", e);
    return [];
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

// ── v4.6 best-fit search: geo + genre layered on the trigram RPC ─────
// We extend search in the route/query layer (PostgREST) rather than the SQL RPC
// because this environment can't apply migrations; the trigram RPC still does
// typo-tolerant name matching, and these add geo + genre intent on top.
// ponytail: no bloom filters — Postgres trigram + GIN indexes already give fuzzy
// matching at this catalog size (~80 festivals / ~700 artists); a bloom filter
// would only help to *avoid* lookups we already do cheaply. Add one only if the
// catalog grows past what trigram scans handle well.

const GENRE_SYNONYMS: Record<string, string[]> = {
  edm: ["electronic", "house", "techno", "dance", "dubstep", "bass"],
  electronic: ["edm", "house", "techno", "dance"],
  "hip hop": ["rap", "hip-hop", "trap"],
  "hip-hop": ["hip hop", "rap", "trap"],
  rap: ["hip hop", "hip-hop", "trap"],
  indie: ["indie rock", "indie pop", "alternative"],
  alt: ["alternative", "alternative rock", "indie"],
  rock: ["alternative rock", "indie rock", "punk", "metal"],
  pop: ["dance-pop", "electropop", "pop rock"],
  country: ["americana", "folk"],
  rnb: ["r&b", "soul", "contemporary r&b"],
  "r&b": ["rnb", "soul", "contemporary r&b"],
};

const US_STATES: Record<string, string> = {
  alabama: "AL", alaska: "AK", arizona: "AZ", arkansas: "AR", california: "CA",
  colorado: "CO", connecticut: "CT", delaware: "DE", florida: "FL", georgia: "GA",
  hawaii: "HI", idaho: "ID", illinois: "IL", indiana: "IN", iowa: "IA",
  kansas: "KS", kentucky: "KY", louisiana: "LA", maine: "ME", maryland: "MD",
  massachusetts: "MA", michigan: "MI", minnesota: "MN", mississippi: "MS",
  missouri: "MO", montana: "MT", nebraska: "NE", nevada: "NV", "new hampshire": "NH",
  "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
  "north dakota": "ND", ohio: "OH", oklahoma: "OK", oregon: "OR", pennsylvania: "PA",
  "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", tennessee: "TN",
  texas: "TX", utah: "UT", vermont: "VT", virginia: "VA", washington: "WA",
  "west virginia": "WV", wisconsin: "WI", wyoming: "WY",
};

const NEARBY_MILES = 150;

function haversineMiles(
  a: { lat: number; lng: number },
  b: { lat: number; lng: number },
): number {
  const R = 3958.8; // earth radius, miles
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

/** Festivals matching a place (city/state), plus nearby festivals by distance. */
async function searchByLocation(q: string): Promise<SearchResult[]> {
  const sb = getSupabase();
  if (!sb) return [];
  const term = q.toLowerCase();
  const stateAbbr = US_STATES[term] ?? (q.length === 2 ? q.toUpperCase() : null);
  try {
    const { data } = await sb
      .from("festivals")
      .select("id, slug, name, city, state, latitude, longitude")
      .eq("is_active", true);
    const all = (data ?? []) as {
      id: string; slug: string; name: string; city: string | null;
      state: string | null; latitude: number | null; longitude: number | null;
    }[];

    const exact = all.filter(
      (f) =>
        (f.city && f.city.toLowerCase().includes(term)) ||
        (f.state && (f.state.toLowerCase() === term || f.state === stateAbbr)),
    );
    if (exact.length === 0) return [];

    const out: SearchResult[] = exact.map((f) => ({
      type: "festival" as const,
      id: f.id,
      slug: f.slug,
      name: f.name,
      description: [f.city, f.state].filter(Boolean).join(", ") || null,
      score: 0.95,
    }));

    // Nearby: other geocoded festivals within NEARBY_MILES of any exact match.
    const centers = exact
      .filter((f) => f.latitude != null && f.longitude != null)
      .map((f) => ({ lat: f.latitude!, lng: f.longitude! }));
    const exactIds = new Set(exact.map((f) => f.id));
    if (centers.length > 0) {
      const nearby: { f: (typeof all)[number]; mi: number }[] = [];
      for (const f of all) {
        if (exactIds.has(f.id) || f.latitude == null || f.longitude == null) continue;
        const mi = Math.min(
          ...centers.map((c) => haversineMiles(c, { lat: f.latitude!, lng: f.longitude! })),
        );
        if (mi <= NEARBY_MILES) nearby.push({ f, mi });
      }
      nearby.sort((a, b) => a.mi - b.mi);
      for (const { f, mi } of nearby.slice(0, 8)) {
        out.push({
          type: "festival",
          id: f.id,
          slug: f.slug,
          name: f.name,
          description: `${Math.round(mi)} mi away · ${[f.city, f.state].filter(Boolean).join(", ")}`,
          score: 0.7 - mi / 1000,
        });
      }
    }
    return out;
  } catch (e) {
    warn("searchByLocation", e);
    return [];
  }
}

/** Artists + festivals matching a genre (with synonym expansion). */
async function searchByGenre(q: string): Promise<SearchResult[]> {
  const sb = getSupabase();
  if (!sb) return [];
  const base = q.toLowerCase();
  const terms = Array.from(new Set([base, ...(GENRE_SYNONYMS[base] ?? [])]));
  try {
    const [artistsRes, festsRes] = await Promise.all([
      sb.from("artists").select("id, slug, name, genres, spotify_popularity")
        .overlaps("genres", terms)
        .order("spotify_popularity", { ascending: false, nullsFirst: false })
        .limit(10),
      sb.from("festivals").select("id, slug, name, tags")
        .overlaps("tags", terms)
        .eq("is_active", true)
        .limit(8),
    ]);
    const out: SearchResult[] = [];
    for (const a of (artistsRes.data ?? []) as { id: string; slug: string; name: string; genres: string[] | null }[]) {
      out.push({
        type: "artist", id: a.id, slug: a.slug, name: a.name,
        description: (a.genres ?? []).slice(0, 3).join(" · ") || null,
        score: 0.85,
      });
    }
    for (const f of (festsRes.data ?? []) as { id: string; slug: string; name: string; tags: string[] | null }[]) {
      out.push({
        type: "festival", id: f.id, slug: f.slug, name: f.name,
        description: `${q} lineup · ${(f.tags ?? []).slice(0, 3).join(", ")}`,
        score: 0.8,
      });
    }
    return out;
  } catch (e) {
    warn("searchByGenre", e);
    return [];
  }
}

/** Substring (ILIKE) name match — catches longer names the trigram RPC misses,
 * e.g. "bonnaroo" → "Bonnaroo Music and Arts Festival". */
async function searchByName(q: string): Promise<SearchResult[]> {
  const sb = getSupabase();
  if (!sb) return [];
  const like = `%${q.replace(/[%_]/g, "")}%`;
  try {
    const [fests, artists] = await Promise.all([
      sb.from("festivals").select("id, slug, name, city, state").ilike("name", like).eq("is_active", true).limit(8),
      sb.from("artists").select("id, slug, name, genres").ilike("name", like).limit(8),
    ]);
    const out: SearchResult[] = [];
    for (const f of (fests.data ?? []) as { id: string; slug: string; name: string; city: string | null; state: string | null }[]) {
      out.push({
        type: "festival", id: f.id, slug: f.slug, name: f.name,
        description: [f.city, f.state].filter(Boolean).join(", ") || null,
        // Prefix matches rank above mid-name matches.
        score: f.name.toLowerCase().startsWith(q.toLowerCase()) ? 0.97 : 0.78,
      });
    }
    for (const a of (artists.data ?? []) as { id: string; slug: string; name: string; genres: string[] | null }[]) {
      out.push({
        type: "artist", id: a.id, slug: a.slug, name: a.name,
        description: (a.genres ?? []).slice(0, 3).join(" · ") || null,
        score: a.name.toLowerCase().startsWith(q.toLowerCase()) ? 0.95 : 0.76,
      });
    }
    return out;
  } catch (e) {
    warn("searchByName", e);
    return [];
  }
}

/**
 * Best-fit unified search (v4.6): trigram name match (RPC) + substring names +
 * location radius + genre intent, merged and de-duped by (type,id), highest
 * score wins.
 */
export async function searchEnhanced(query: string): Promise<SearchResult[]> {
  const q = query.trim();
  if (q.length === 0) return [];
  const [base, byName, location, genre] = await Promise.all([
    searchAll(q),
    searchByName(q),
    searchByLocation(q),
    searchByGenre(q),
  ]);
  const merged = new Map<string, SearchResult>();
  for (const r of [base, byName, location, genre].flat()) {
    const key = `${r.type}:${r.id}`;
    const prev = merged.get(key);
    if (!prev || r.score > prev.score) {
      // Keep the most informative description when scores tie/replace.
      merged.set(key, { ...r, description: r.description ?? prev?.description ?? null });
    }
  }
  return [...merged.values()].sort((a, b) => b.score - a.score).slice(0, 30);
}

/** Recent ingestion runs for the observability dashboard (v3.11). Public-read. */
export async function getRecentIngestionRuns(
  limit = 80,
): Promise<IngestionRunSummary[]> {
  const sb = getSupabase();
  if (!sb) return [];
  try {
    const { data, error } = await sb
      .from("ingestion_runs")
      .select("festival_slug, status, started_at, finished_at, rows_upserted, rows_skipped")
      .order("started_at", { ascending: false })
      .limit(limit);
    if (error) throw error;
    return (data as IngestionRunSummary[]) ?? [];
  } catch (e) {
    warn("getRecentIngestionRuns", e);
    return [];
  }
}

/** Published editorial guide for a festival, newest first (v3.9). */
export async function getFestivalGuide(
  festivalId: string,
): Promise<FestivalGuide | null> {
  const sb = getSupabase();
  if (!sb) return null;
  try {
    const { data, error } = await sb
      .from("festival_guides")
      .select("id, festival_id, slug, title, body_md, author, published_at")
      .eq("festival_id", festivalId)
      .not("published_at", "is", null)
      .order("published_at", { ascending: false })
      .limit(1);
    if (error) throw error;
    return ((data as FestivalGuide[]) ?? [])[0] ?? null;
  } catch (e) {
    warn("getFestivalGuide", e);
    return null;
  }
}

/** "Did you mean?" suggestions — closest names regardless of % threshold (v3.3). */
export async function searchSuggest(query: string): Promise<Suggestion[]> {
  const sb = getSupabase();
  const q = query.trim();
  if (!sb || q.length === 0) return [];
  try {
    const { data, error } = await sb.rpc("search_suggest", { query: q });
    if (error) throw error;
    return (data as Suggestion[]) ?? [];
  } catch (e) {
    warn("searchSuggest", e);
    return [];
  }
}

// ── Convenience: festival page bundle ──────────────────────────

export interface FestivalComparison {
  self: { artists: number; avgPop: number | null };
  pastYears: { year: number; artists: number; avgPop: number | null }[];
  peers: { slug: string; name: string; artists: number; avgPop: number | null }[];
}

interface PopRow {
  festival_id: string;
  year: number | null;
  artist_id: string;
  artists: { spotify_popularity: number | null } | null;
}

/** Aggregate distinct-artist count + avg Spotify popularity per (festival, year). */
function aggregate(rows: PopRow[]): Map<string, { artists: Set<string>; pops: number[] }> {
  const m = new Map<string, { artists: Set<string>; pops: number[] }>();
  for (const r of rows) {
    const key = `${r.festival_id}__${r.year ?? "?"}`;
    if (!m.has(key)) m.set(key, { artists: new Set(), pops: [] });
    const bucket = m.get(key)!;
    bucket.artists.add(r.artist_id);
    const pop = r.artists?.spotify_popularity;
    if (pop != null) bucket.pops.push(pop);
  }
  return m;
}

const avg = (xs: number[]) =>
  xs.length ? Math.round(xs.reduce((s, x) => s + x, 0) / xs.length) : null;

/**
 * Comparison data for the lineup-analysis "Comparisons" panel (v4.6): this
 * festival vs its own past years, and vs similar (peer) festivals' current year.
 * Peers are the already-fetched related festivals, so this is two extra queries.
 */
export async function getFestivalComparison(
  festival: Festival,
  year: number,
  peers: Festival[],
): Promise<FestivalComparison | null> {
  const sb = getSupabase();
  if (!sb) return null;
  try {
    const POP = "festival_id, year, artist_id, artists(spotify_popularity)";
    const peerIds = peers.map((p) => p.id);
    const [ownRes, peerRes] = await Promise.all([
      sb.from("lineups").select(POP).eq("festival_id", festival.id),
      peerIds.length
        ? sb.from("lineups").select(POP).in("festival_id", peerIds).eq("year", year)
        : Promise.resolve({ data: [] as PopRow[], error: null }),
    ]);
    if (ownRes.error) throw ownRes.error;

    const own = aggregate((ownRes.data as unknown as PopRow[]) ?? []);
    const self = own.get(`${festival.id}__${year}`);
    const pastYears = [...own.entries()]
      .map(([k, v]) => ({
        year: Number(k.split("__")[1]),
        artists: v.artists.size,
        avgPop: avg(v.pops),
      }))
      .filter((p) => p.year !== year && !Number.isNaN(p.year))
      .sort((a, b) => b.year - a.year)
      .slice(0, 4);

    const peerAgg = aggregate((peerRes.data as unknown as PopRow[]) ?? []);
    const byId = new Map(peers.map((p) => [p.id, p]));
    const peerStats = [...peerAgg.entries()]
      .map(([k, v]) => {
        const p = byId.get(k.split("__")[0]);
        return p
          ? { slug: p.slug, name: p.name, artists: v.artists.size, avgPop: avg(v.pops) }
          : null;
      })
      .filter((x): x is NonNullable<typeof x> => x != null)
      .sort((a, b) => b.artists - a.artists)
      .slice(0, 4);

    return {
      self: { artists: self?.artists.size ?? 0, avgPop: avg(self?.pops ?? []) },
      pastYears,
      peers: peerStats,
    };
  } catch (e) {
    warn("getFestivalComparison", e);
    return null;
  }
}

export interface FestivalPageData {
  festival: Festival;
  year: number;
  lineup: LineupEntry[];
  related: Festival[];
  comparison: FestivalComparison | null;
}

export async function getFestivalPageData(
  slug: string,
): Promise<FestivalPageData | null> {
  const festival = await getFestivalBySlug(slug);
  if (!festival) return null;
  const year = festivalYear(festival.start_date);
  const [lineup, related] = await Promise.all([
    getLineup(festival.id, year),
    getRelatedFestivals(festival),
  ]);
  const comparison = await getFestivalComparison(festival, year, related);
  return { festival, year, lineup, related, comparison };
}
