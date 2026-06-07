import Image from "next/image";
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
          className="object-cover"
        />
      ) : (
        <div
          className="absolute inset-0"
          style={{ backgroundImage: accentGradient(accent) }}
          aria-hidden
        />
      )}
      <div className="hero-scrim absolute inset-0" />

      <div className="relative mx-auto w-full max-w-wide px-5 pb-16 pt-32 md:px-8">
        <p className="mb-4 text-label uppercase tracking-[0.2em] text-white/80">
          {formatLocation(festival.city, festival.state)}
          {festival.venue ? ` · ${festival.venue}` : ""}
        </p>
        <h1 className="text-display-xl text-white">{festival.name}</h1>
        <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-3">
          <span className="text-body-lg text-white">
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
