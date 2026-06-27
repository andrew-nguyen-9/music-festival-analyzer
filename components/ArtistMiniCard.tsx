import Link from "next/link";

// Shared artist tile used by the recommendation rails (SimilarArtists, ForYou).
// One source of truth for the card's link scheme, hover styling, and genre line.
export default function ArtistMiniCard({
  slug,
  name,
  genres,
}: {
  slug: string;
  name: string;
  genres: string[];
}) {
  return (
    <Link
      href={`/artist/${slug}`}
      className="group rounded-2xl border border-white/10 bg-white/5 p-4 transition-colors hover:border-accent hover:bg-white/10"
    >
      <span className="block truncate font-medium text-white group-hover:text-accent">
        {name}
      </span>
      {genres.length > 0 && (
        <span className="mt-1 block truncate text-xs text-white/50">
          {genres.slice(0, 2).join(" · ")}
        </span>
      )}
    </Link>
  );
}
