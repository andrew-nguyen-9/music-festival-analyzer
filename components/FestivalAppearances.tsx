import Link from "next/link";
import Reveal from "./Reveal";
import EmptyState from "./EmptyState";
import { formatDateRange, formatLocation } from "@/lib/format";
import type { ArtistAppearance } from "@/lib/types";

interface Props {
  appearances: ArtistAppearance[];
  artistName: string;
}

export default function FestivalAppearances({
  appearances,
  artistName,
}: Props) {
  return (
    <section className="mx-auto max-w-wide px-5 py-16 md:px-8">
      <Reveal>
        <h2 className="mb-8 text-display-lg text-white">Festival appearances</h2>
      </Reveal>

      {appearances.length === 0 ? (
        <EmptyState
          title="No appearances yet"
          hint={`${artistName} isn't linked to any festival lineups in the database yet.`}
        />
      ) : (
        <ul className="divide-y divide-white/10 overflow-hidden rounded-2xl border border-white/10 bg-surface-elevated">
          {appearances.map((a) => (
            <li key={a.id}>
              <Link
                href={`/festival/${a.festival.slug}`}
                className="group flex items-center justify-between gap-4 px-5 py-4 transition-colors hover:bg-white/5"
              >
                <div className="flex items-center gap-4">
                  <span
                    className="hidden h-10 w-1.5 rounded-full sm:block"
                    style={{ backgroundColor: a.festival.accent_color ?? "#FF4500" }}
                    aria-hidden
                  />
                  <div>
                    <p className="text-body-lg font-semibold text-white">
                      {a.festival.name}
                    </p>
                    <p className="text-label text-[color:var(--text-muted)]">
                      {formatLocation(a.festival.city, a.festival.state)}
                      {a.stage ? ` · ${a.stage}` : ""}
                      {a.is_headliner ? " · Headliner" : ""}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-label text-white/80">{a.year}</p>
                  <p className="hidden text-label text-[color:var(--text-muted)] sm:block">
                    {formatDateRange(a.festival.start_date, a.festival.end_date)}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
