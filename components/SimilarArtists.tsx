import ArtistMiniCard from "@/components/ArtistMiniCard";
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
          <ArtistMiniCard key={a.slug} slug={a.slug} name={a.name} genres={a.genres} />
        ))}
      </div>
    </section>
  );
}
