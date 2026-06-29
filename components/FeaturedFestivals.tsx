import FestivalCard from "./FestivalCard";
import Reveal from "./Reveal";
import type { Festival } from "@/lib/types";

interface Props {
  festivals: Festival[];
}

/**
 * Featured festivals as a horizontal, scroll-snap carousel (v4.5). Only festivals
 * with real (non-estimated) data reach here — see getFeaturedFestivals. Uses
 * native overflow scrolling (no JS animation), so it is reduced-motion safe; the
 * heading reveal already respects prefers-reduced-motion via <Reveal>.
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
      <ul
        className="no-scrollbar mx-auto flex max-w-wide snap-x snap-mandatory gap-4 overflow-x-auto px-5 pb-2 md:px-8"
        aria-label="Featured festivals carousel"
      >
        {festivals.map((f, i) => (
          <li key={f.id} className="w-64 shrink-0 snap-start sm:w-72">
            <FestivalCard festival={f} priority={i < 3} />
          </li>
        ))}
      </ul>
    </section>
  );
}
