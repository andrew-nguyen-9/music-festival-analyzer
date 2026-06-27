import Link from "next/link";
import type { SimilarArtist } from "@/lib/recommendations";

// "Fans also like" — precomputed artist neighbours (v3.6). Presentational; the
// page passes data in. Renders nothing when there are no neighbours yet.
export default function SimilarArtists({
  artists,
  name,
}: {
  artists: SimilarArtist[];
  name: string;
}) {
  if (!artists.length) return null;
  return (
    <section className="mx-auto max-w-wide px-5 py-16 md:px-8">
      <h2 className="mb-8 text-heading font-semibold text-white">
        If you like {name}
      </h2>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
        {artists.map((a) => (
          <Link
            key={a.slug}
            href={`/artist/${a.slug}`}
            className="group rounded-2xl border border-white/10 bg-white/5 p-4 transition-colors hover:border-accent hover:bg-white/10"
          >
            <span className="block truncate font-medium text-white group-hover:text-accent">
              {a.name}
            </span>
            {a.genres.length > 0 && (
              <span className="mt-1 block truncate text-xs text-white/50">
                {a.genres.slice(0, 2).join(" · ")}
              </span>
            )}
          </Link>
        ))}
      </div>
    </section>
  );
}
