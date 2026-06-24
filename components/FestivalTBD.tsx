import type { Festival } from "@/lib/types";
import { formatDateRange, formatLocation } from "@/lib/format";

interface Props {
  festival: Festival;
}

export default function FestivalTBD({ festival }: Props) {
  return (
    <section className="mx-auto max-w-wide px-5 py-20 md:px-8">
      <div className="flex flex-col items-start gap-6">
        {/* Upcoming pill */}
        <span
          className="rounded-full px-4 py-1.5 text-label font-semibold uppercase tracking-widest text-white"
          style={{ background: "var(--upcoming)", color: "#fff" }}
        >
          Lineup TBA
        </span>

        <h2 className="text-display-lg text-white">
          {festival.name}
        </h2>

        <div className="flex flex-wrap gap-6 text-body-lg text-white/60">
          {(festival.city || festival.state) && (
            <span>
              📍{" "}
              {formatLocation(festival.city, festival.state)}
              {festival.venue ? ` · ${festival.venue}` : ""}
            </span>
          )}
          {festival.start_date && (
            <span>
              📅 {formatDateRange(festival.start_date, festival.end_date)}
            </span>
          )}
        </div>

        {festival.description && (
          <p className="max-w-2xl text-body-lg leading-relaxed text-white/70">
            {festival.description}
          </p>
        )}

        <div
          className="rounded-2xl border px-8 py-6"
          style={{
            borderColor: "var(--upcoming)",
            background: "color-mix(in srgb, var(--upcoming) 8%, transparent)",
          }}
        >
          <p
            className="text-heading font-semibold"
            style={{ color: "var(--upcoming-light)" }}
          >
            Lineup not yet announced
          </p>
          <p className="mt-2 text-body text-white/55">
            Check back soon — we&apos;ll update this page the moment the
            lineup drops.
          </p>
          {festival.website_url && (
            <a
              href={festival.website_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 inline-flex items-center gap-2 text-label font-semibold transition-opacity hover:opacity-80"
              style={{ color: "var(--upcoming-light)" }}
            >
              Visit official site →
            </a>
          )}
        </div>
      </div>
    </section>
  );
}
