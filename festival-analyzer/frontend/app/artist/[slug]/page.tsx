import { notFound } from "next/navigation";
import type { Metadata } from "next";
import FestivalThemeStyle from "@/components/FestivalThemeStyle";
import ArtistHero from "@/components/ArtistHero";
import StreamingWidget from "@/components/StreamingWidget";
import FestivalAppearances from "@/components/FestivalAppearances";
import { getArtistBySlug, getArtistAppearances } from "@/lib/queries";

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
  const artist = await getArtistBySlug(slug);
  if (!artist) notFound();

  const appearances = await getArtistAppearances(artist.id);
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

      <StreamingWidget artist={artist} />
      <FestivalAppearances
        appearances={appearances}
        artistName={artist.name}
      />
    </FestivalThemeStyle>
  );
}
