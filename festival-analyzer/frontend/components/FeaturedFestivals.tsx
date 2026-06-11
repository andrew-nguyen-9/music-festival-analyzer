import FestivalCard from "./FestivalCard";
import Reveal from "./Reveal";
import type { Festival } from "@/lib/types";

interface Props {
  festivals: Festival[];
}

export default function FeaturedFestivals({ festivals }: Props) {
  if (festivals.length === 0) return null;
  return (
    <section className="py-8">
      <div className="mx-auto max-w-wide px-5 md:px-8">
        <Reveal>
          <h2 className="mb-5 text-heading font-semibold text-white">Featured</h2>
        </Reveal>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {festivals.map((f, i) => (
            <FestivalCard key={f.id} festival={f} priority={i < 4} />
          ))}
        </div>
      </div>
    </section>
  );
}
