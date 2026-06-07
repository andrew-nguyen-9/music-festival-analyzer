import { notFound } from "next/navigation";
import type { Metadata } from "next";
import FestivalThemeStyle from "@/components/FestivalThemeStyle";
import FestivalHero from "@/components/FestivalHero";
import LineupGrid from "@/components/LineupGrid";
import MediaGallery from "@/components/MediaGallery";
import SocialFeed from "@/components/SocialFeed";
import FunFactsWidget from "@/components/FunFactsWidget";
import RelatedFestivals from "@/components/RelatedFestivals";
import { getFestivalBySlug, getFestivalPageData } from "@/lib/queries";

export const dynamic = "force-dynamic";

interface PageProps {
  params: { slug: string };
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const festival = await getFestivalBySlug(params.slug);
  if (!festival) return { title: "Festival not found" };
  return {
    title: festival.name,
    description:
      festival.description ??
      `${festival.name} lineup, artists, photos and more.`,
    openGraph: festival.hero_image_url
      ? { images: [festival.hero_image_url] }
      : undefined,
  };
}

export default async function FestivalPage({ params }: PageProps) {
  const data = await getFestivalPageData(params.slug);
  if (!data) notFound();

  const { festival, year, lineup, media, social, funFacts, related } = data;

  return (
    <FestivalThemeStyle accentColor={festival.accent_color}>
      <FestivalHero festival={festival} />

      {festival.description && (
        <section className="mx-auto max-w-3xl px-5 py-16 md:px-8">
          <p className="text-body-lg leading-relaxed text-white/85">
            {festival.description}
          </p>
        </section>
      )}

      <LineupGrid lineup={lineup} />
      <MediaGallery media={media} />
      <SocialFeed posts={social} />
      <FunFactsWidget facts={funFacts} festivalName={festival.name} year={year} />
      <RelatedFestivals festivals={related} />
    </FestivalThemeStyle>
  );
}
