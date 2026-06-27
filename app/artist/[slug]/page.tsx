import { notFound } from "next/navigation";
import type { Metadata } from "next";
import FestivalThemeStyle from "@/components/FestivalThemeStyle";
import ArtistHero from "@/components/ArtistHero";
import StreamingWidget from "@/components/StreamingWidget";
import ArtistDiscography from "@/components/ArtistDiscography";
import FestivalAppearances from "@/components/FestivalAppearances";
import SimilarArtists from "@/components/SimilarArtists";
import EmptyState from "@/components/EmptyState";
import {
  getArtistBySlug,
  getArtistAppearances,
  getArtistSpotifyCache,
  withSpotifyCache,
} from "@/lib/queries";
import { getSimilarArtists } from "@/lib/recommendations";

export const dynamic = "force-dynamic";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const artist = await getArtistBySlug(slug);
  if (!artist) return { title: "Artist not found" };
  return {
    title: artist.name,
    description:
      artist.bio ?? `${artist.name} — bio, music, and festival appearances.`,
  };
}

export default async function ArtistPage({ params }: PageProps) {
  const { slug } = await params;
  const base = await getArtistBySlug(slug);
  if (!base) notFound();

  // Overlay cached Spotify data (v2.2) — read from cache, never from Spotify.
  const [cache, appearances, similar] = await Promise.all([
    getArtistSpotifyCache(base.id),
    getArtistAppearances(base.id),
    getSimilarArtists(base.id),
  ]);
  const artist = withSpotifyCache(base, cache);
  // Thin-data artist: nothing enriched yet beyond a name. Render an honest
  // "still gathering" note instead of a near-empty page (v2.4.4).
  const thin =
    !artist.bio &&
    !artist.spotify_id &&
    !artist.preview_url &&
    (artist.genres?.length ?? 0) === 0;
  // Theme the page by the artist's headliner/first festival accent, if any.
  const themeAccent =
    appearances.find((a) => a.is_headliner)?.festival.accent_color ??
    appearances[0]?.festival.accent_color ??
    "#7B2FBE";

  return (
    <FestivalThemeStyle accentColor={themeAccent}>
      <ArtistHero artist={artist} />

      {artist.bio && (
        <section className="mx-auto max-w-3xl px-5 py-16 md:px-8">
          <h2 className="mb-6 text-heading font-semibold text-white">About</h2>
          <p className="text-body-lg leading-relaxed text-white/85">
            {artist.bio}
          </p>
        </section>
      )}

      {thin ? (
        <section className="mx-auto max-w-3xl px-5 py-16 md:px-8">
          <EmptyState
            title="Still gathering data on this artist"
            hint="Bio, music, and stats appear once the Spotify sync worker matches this artist. Their festival appearances are below."
          />
        </section>
      ) : (
        <>
          <StreamingWidget artist={artist} />
          {artist.spotify_id && (
            <ArtistDiscography
              spotifyId={artist.spotify_id}
              artistName={artist.name}
            />
          )}
        </>
      )}
      <FestivalAppearances
        appearances={appearances}
        artistName={artist.name}
      />
      <SimilarArtists artists={similar} name={artist.name} />
    </FestivalThemeStyle>
  );
}
