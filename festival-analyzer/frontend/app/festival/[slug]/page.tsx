import { notFound } from "next/navigation";
import type { Metadata } from "next";
import FestivalThemeStyle from "@/components/FestivalThemeStyle";
import FestivalHero from "@/components/FestivalHero";
import FestivalPassedBanner from "@/components/FestivalPassedBanner";
import FestivalTBD from "@/components/FestivalTBD";
import LineupGrid from "@/components/LineupGrid";
import LineupByPopularity from "@/components/LineupByPopularity";
import LineupByDay from "@/components/LineupByDay";
import MediaGallery from "@/components/MediaGallery";
import SocialFeed from "@/components/SocialFeed";
import FunFactsWidget from "@/components/FunFactsWidget";
import RelatedFestivals from "@/components/RelatedFestivals";
import { getFestivalBySlug, getFestivalPageData } from "@/lib/queries";
import { getFestivalState } from "@/lib/format";

export const dynamic = "force-dynamic";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const festival = await getFestivalBySlug(slug);
  if (!festival) return { title: "Festival not found" };
  return {
    title: festival.name,
    description:
      festival.description ?? `${festival.name} lineup, artists, photos and more.`,
    openGraph: festival.hero_image_url ? { images: [festival.hero_image_url] } : undefined,
  };
}

export default async function FestivalPage({ params }: PageProps) {
  const { slug } = await params;
  const data = await getFestivalPageData(slug);
  if (!data) notFound();

  const { festival, year, lineup, media, social, funFacts, related } = data;

  const hasSchedule = lineup.some((e) => e.day != null);
  const state = getFestivalState(festival.end_date, lineup.length, hasSchedule);
  const isPassed = state === "passed";

  // For passed festivals: apply grayscale + reduced opacity to the content.
  const passedStyle = isPassed
    ? { filter: "grayscale(0.85) brightness(0.65)", transition: "filter 0.3s ease" }
    : undefined;

  return (
    <FestivalThemeStyle accentColor={isPassed ? "#6b7280" : festival.accent_color}>
      {/* "See you next year" banner — top of page before the hero */}
      {isPassed && <FestivalPassedBanner festival={festival} />}

      <div style={passedStyle}>
        <FestivalHero festival={festival} />

        {festival.description && (
          <section className="mx-auto max-w-3xl px-5 py-16 md:px-8">
            <p className="text-body-lg leading-relaxed text-white/85">
              {festival.description}
            </p>
          </section>
        )}

        {/* Lineup section — varies by state */}
        {state === "tbd" && <FestivalTBD festival={festival} />}
        {state === "lineup" && <LineupByPopularity lineup={lineup} />}
        {state === "schedule" && <LineupByDay lineup={lineup} />}
        {state === "passed" && <LineupGrid lineup={lineup} />}

        <MediaGallery media={media} />
        <SocialFeed posts={social} />
        <FunFactsWidget facts={funFacts} festivalName={festival.name} year={year} />
        <RelatedFestivals festivals={related} />
      </div>
    </FestivalThemeStyle>
  );
}
