import HeroSection from "@/components/HeroSection";
import FeaturedFestivals from "@/components/FeaturedFestivals";
import FestivalGrid from "@/components/FestivalGrid";
import { getFestivals, getFeaturedFestivals } from "@/lib/queries";

// Live data — render at request time.
export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [festivals, featured] = await Promise.all([
    getFestivals(),
    getFeaturedFestivals(8),
  ]);

  return (
    <>
      <HeroSection />
      <FeaturedFestivals festivals={featured} />
      <div className="mx-auto max-w-wide px-5 md:px-8">
        <h2 className="text-heading font-semibold text-white">
          All Festivals
        </h2>
      </div>
      <FestivalGrid festivals={festivals} />
    </>
  );
}
