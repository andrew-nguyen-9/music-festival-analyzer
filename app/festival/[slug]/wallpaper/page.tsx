import { notFound } from "next/navigation";
import type { Metadata } from "next";
import FestivalThemeStyle from "@/components/FestivalThemeStyle";
import WallpaperStudio from "@/components/WallpaperStudio";
import { getFestivalBySlug, getLineup, getStages } from "@/lib/queries";
import { festivalYear } from "@/lib/format";

export const dynamic = "force-dynamic";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const festival = await getFestivalBySlug(slug);
  return {
    title: festival ? `${festival.name} wallpaper` : "Wallpaper",
    description: "Build a phone wallpaper of your festival day — set times and stages.",
  };
}

export default async function WallpaperPage({ params }: PageProps) {
  const { slug } = await params;
  const festival = await getFestivalBySlug(slug);
  if (!festival) notFound();

  const year = festivalYear(festival.start_date);
  const [lineup, stages] = await Promise.all([
    getLineup(festival.id, year),
    getStages(festival.id),
  ]);

  return (
    <FestivalThemeStyle accentColor={festival.accent_color}>
      <WallpaperStudio festival={festival} lineup={lineup} stages={stages} />
    </FestivalThemeStyle>
  );
}
