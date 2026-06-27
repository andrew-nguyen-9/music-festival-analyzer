import { notFound } from "next/navigation";
import type { Metadata } from "next";
import FestivalThemeStyle from "@/components/FestivalThemeStyle";
import FestivalHero from "@/components/FestivalHero";
import FestivalPassedBanner from "@/components/FestivalPassedBanner";
import FestivalPageTabs from "@/components/FestivalPageTabs";
import MediaGallery from "@/components/MediaGallery";
import SocialFeed from "@/components/SocialFeed";
import FunFactsWidget from "@/components/FunFactsWidget";
import RelatedFestivals from "@/components/RelatedFestivals";
import FestivalGuide from "@/components/FestivalGuide";
import SmartPlaylistButton from "@/components/SmartPlaylistButton";
import Link from "next/link";
import { getFestivalBySlug, getFestivalPageData, getFestivalGuide } from "@/lib/queries";
import { getFestivalState, groupLineupByDay } from "@/lib/format";

// ISR (v3.10): cache the rendered page, refresh every 10 min. Festival data
// changes at most daily (cron), so on-demand ISR is a large TTFB win at catalog
// scale vs. force-dynamic, with acceptable staleness.
export const revalidate = 600;

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
  const guide = await getFestivalGuide(festival.id);

  const hasSchedule = lineup.some((e) => e.day != null);
  const state = getFestivalState(festival.end_date, lineup.length, hasSchedule);

  // Lineup artist ids grouped by day for the per-day playlist (v2.11.2).
  const dayGroups = [...groupLineupByDay(lineup).entries()]
    .map(([key, entries]) => ({ key, artistIds: entries.map((e) => e.artist.id) }))
    .sort((a, b) =>
      a.key === "TBD" ? 1 : b.key === "TBD" ? -1 : a.key.localeCompare(b.key),
    );
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

        <FestivalPageTabs festival={festival} lineup={lineup} state={state} />

        {!isPassed && lineup.length > 0 && (
          <section className="mx-auto flex max-w-wide flex-wrap items-center gap-4 px-5 py-4 md:px-8">
            {hasSchedule && (
              <Link
                href={`/festival/${festival.slug}/wallpaper`}
                className="inline-flex items-center gap-2 rounded-full bg-accent px-6 py-3 text-label font-semibold uppercase tracking-wide text-black transition-transform hover:scale-[1.02]"
              >
                📱 Make a phone wallpaper of your day
              </Link>
            )}
            <SmartPlaylistButton
              festivalName={festival.name}
              year={year}
              days={dayGroups}
            />
          </section>
        )}

        <FestivalGuide guide={guide} />
        <MediaGallery media={media} />
        <SocialFeed posts={social} />
        <FunFactsWidget facts={funFacts} festivalName={festival.name} year={year} />
        <RelatedFestivals festivals={related} />
      </div>
    </FestivalThemeStyle>
  );
}
