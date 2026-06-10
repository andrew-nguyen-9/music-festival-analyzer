"use client";

import Image from "next/image";
import Link from "next/link";
import Reveal from "./Reveal";
import { accentGradient } from "@/lib/festival-theme";
import type { LineupEntry } from "@/lib/types";

interface Props {
  lineup: LineupEntry[];
}

export default function LineupByPopularity({ lineup }: Props) {
  const sorted = [...lineup].sort((a, b) => {
    if (a.is_headliner !== b.is_headliner) return a.is_headliner ? -1 : 1;
    return (b.artist.spotify_popularity ?? 0) - (a.artist.spotify_popularity ?? 0);
  });

  const headliners = sorted.filter((e) => e.is_headliner);
  const rest = sorted.filter((e) => !e.is_headliner);

  return (
    <section className="mx-auto max-w-wide px-5 py-16 md:px-8">
      <Reveal>
        <h2 className="mb-2 text-display-lg text-white">Lineup</h2>
        <p className="mb-10 text-label uppercase tracking-widest text-white/40">
          Sorted by popularity · Schedule TBA
        </p>
      </Reveal>

      {headliners.length > 0 && (
        <div className="mb-12">
          <h3 className="mb-5 text-heading font-semibold text-accent">Headliners</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {headliners.map((entry, i) => (
              <Reveal key={entry.id} delay={i * 0.06}>
                <ArtistCard entry={entry} large />
              </Reveal>
            ))}
          </div>
        </div>
      )}

      {rest.length > 0 && (
        <div>
          <h3 className="mb-5 text-heading font-semibold text-white/60">
            {headliners.length > 0 ? "More Artists" : "Artists"}
          </h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {rest.map((entry, i) => (
              <Reveal key={entry.id} delay={Math.min(i * 0.03, 0.4)}>
                <ArtistCard entry={entry} />
              </Reveal>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function ArtistCard({ entry, large = false }: { entry: LineupEntry; large?: boolean }) {
  const { artist } = entry;
  const img = artist.image_url ?? artist.header_image_url;

  return (
    <Link
      href={`/artist/${artist.slug}`}
      className="group relative block overflow-hidden rounded-xl border border-white/10 bg-surface-elevated"
    >
      <div className={`relative w-full overflow-hidden ${large ? "aspect-[4/3]" : "aspect-square"}`}>
        {img ? (
          <Image
            src={img}
            alt={artist.name}
            fill
            sizes={large ? "(max-width: 640px) 100vw, 33vw" : "(max-width: 640px) 50vw, 25vw"}
            className="object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div
            className="h-full w-full"
            style={{ backgroundImage: accentGradient(null) }}
            aria-hidden
          />
        )}
        <div className="hero-scrim absolute inset-0 opacity-90" />
        <div className="absolute inset-x-0 bottom-0 p-3">
          <p className={`font-semibold leading-tight text-white ${large ? "text-display-md" : "text-body-lg"}`}>
            {artist.name}
          </p>
          {artist.genres?.length > 0 && (
            <p className="mt-0.5 truncate text-[11px] uppercase tracking-wide text-white/60">
              {artist.genres.slice(0, 2).join(" · ")}
            </p>
          )}
        </div>
      </div>
    </Link>
  );
}
