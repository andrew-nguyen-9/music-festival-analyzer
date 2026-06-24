import FestivalCard from "./FestivalCard";
import Reveal from "./Reveal";
import type { Festival } from "@/lib/types";

interface Props {
  festivals: Festival[];
}

export default function RelatedFestivals({ festivals }: Props) {
  if (festivals.length === 0) return null;
  return (
    <section className="mx-auto max-w-wide px-5 py-16 md:px-8">
      <Reveal>
        <h2 className="mb-8 text-display-lg text-white">Similar festivals</h2>
      </Reveal>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {festivals.map((f) => (
          <FestivalCard key={f.id} festival={f} />
        ))}
      </div>
    </section>
  );
}
