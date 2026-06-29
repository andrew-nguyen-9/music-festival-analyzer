import Image from "next/image";
import ScrollScaleTitle from "./ScrollScaleTitle";
import { accentGradient } from "@/lib/festival-theme";
import { formatDateRange, formatLocation } from "@/lib/format";
import type { Festival } from "@/lib/types";

interface Props {
  festival: Festival;
}

export default function FestivalHero({ festival }: Props) {
  const accent = festival.accent_color ?? "#FF4500";
  return (
    <section className="relative flex min-h-[92vh] flex-col justify-end overflow-hidden">
      {festival.hero_image_url ? (
        <Image
          src={festival.hero_image_url}
          alt={festival.name}
          fill
          priority
          sizes="100vw"
          className="object-cover object-top"
        />
      ) : festival.vector_art ? (
        <div
          className="absolute inset-0 [&>svg]:h-full [&>svg]:w-full [&>svg]:object-cover"
          dangerouslySetInnerHTML={{ __html: festival.vector_art }}
          aria-hidden
        />
      ) : (
        <div
          className="absolute inset-0"
          style={{ backgroundImage: accentGradient(accent) }}
          aria-hidden
        />
      )}
      <div className="hero-scrim absolute inset-0" />

      <div className="over-media relative mx-auto w-full max-w-wide px-5 pb-16 pt-32 md:px-8">
        <p className="mb-4 text-label uppercase tracking-[0.2em] text-white/80">
          {formatLocation(festival.city, festival.state)}
          {festival.venue ? ` · ${festival.venue}` : ""}
        </p>
        <ScrollScaleTitle
          name={festival.name}
          className="text-display-xl text-white"
        />
        <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-3">
          <span className="text-body-lg text-white">
            {festival.dates_estimated && (
              <span title="Estimated date — not yet officially announced" className="mr-1 text-white/50">~</span>
            )}
            {formatDateRange(festival.start_date, festival.end_date)}
          </span>
          {festival.website_url && (
            <a
              href={festival.website_url}
              target="_blank"
              rel="noreferrer"
              className="rounded-full px-4 py-2 text-label font-semibold uppercase tracking-wide text-black transition-transform hover:scale-105"
              style={{ backgroundColor: accent }}
            >
              Official site ↗
            </a>
          )}
        </div>
        {festival.tags?.length > 0 && (
          <div className="mt-5 flex flex-wrap gap-2">
            {festival.tags.map((t) => (
              <span
                key={t}
                className="rounded-full border border-white/25 bg-black/30 px-3 py-1 text-label uppercase tracking-wide text-white/85 backdrop-blur"
              >
                {t}
              </span>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
