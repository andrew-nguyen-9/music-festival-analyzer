interface Props {
  spotifyId: string;
  artistName: string;
}

/**
 * Discography link-out. The artist's top tracks are already played by the
 * StreamingWidget ("Listen") embed above, so this no longer renders a second
 * identical Spotify player (that was the duplication — "Listen" and the old
 * "Top Songs"/"Albums" embeds were all the same artist embed). Albums have no
 * standalone artist-embed variant and the frontend has no Spotify secret to fetch
 * them server-side, so the full discography is a direct link to Spotify.
 */
export default function ArtistDiscography({ spotifyId, artistName }: Props) {
  const artistUrl = `https://open.spotify.com/artist/${spotifyId}`;

  return (
    <section className="mx-auto max-w-wide px-5 pb-12 md:px-8">
      <h2 className="mb-6 text-display-lg text-white">Discography</h2>
      <a
        href={artistUrl}
        target="_blank"
        rel="noreferrer"
        className="flex items-center justify-between gap-4 rounded-2xl border border-white/10 bg-surface-elevated px-5 py-4 transition-colors hover:border-white/25"
      >
        <span>
          <span className="block font-semibold text-white">
            Browse {artistName}&apos;s albums &amp; singles
          </span>
          <span className="block text-label text-white/50">
            Full discography on Spotify
          </span>
        </span>
        <span className="shrink-0 rounded-full bg-accent px-4 py-2 text-label font-semibold uppercase tracking-wide text-black">
          Open ↗
        </span>
      </a>
    </section>
  );
}
