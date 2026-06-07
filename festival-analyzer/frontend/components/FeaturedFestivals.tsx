import FestivalCard from "./FestivalCard";
import Reveal from "./Reveal";
import type { Festival } from "@/lib/types";

interface Props {
  festivals: Festival[];
}

/**
 * Horizontal-scroll strip of flagship festivals. Snap scrolling, hidden
 * scrollbar. (Heavier scroll choreography is a later polish pass.)
 */
export default function FeaturedFestivals({ festivals }: Props) {
  if (festivals.length === 0) return null;
  return (
    <section className="py-8">
      <div className="mx-auto max-w-wide px-5 md:px-8">
        <Reveal>
          <h2 className="mb-5 text-heading font-semibold text-white">
            Featured
          </h2>
        </Reveal>
      </div>
      <div className="no-scrollbar flex snap-x snap-mandatory gap-4 overflow-x-auto px-5 pb-2 md:px-8">
        {festivals.map((f, i) => (
          <div
            key={f.id}
            className="w-[78vw] shrink-0 snap-start sm:w-[46vw] lg:w-[30vw] xl:w-[24rem]"
          >
            <FestivalCard festival={f} priority={i < 2} />
          </div>
        ))}
      </div>
    </section>
  );
}
