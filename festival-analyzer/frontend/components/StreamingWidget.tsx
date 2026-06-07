import MusicPlayerToggle from "./MusicPlayerToggle";
import type { Artist } from "@/lib/types";

interface Props {
  artist: Artist;
}

/** Artist streaming block: service toggle + external links. */
export default function StreamingWidget({ artist }: Props) {
  return (
    <section className="mx-auto max-w-wide px-5 py-16 md:px-8">
      <h2 className="mb-8 text-display-lg text-white">Listen</h2>
      <div className="grid gap-6 lg:grid-cols-[1fr,auto]">
        <MusicPlayerToggle
          spotifyId={artist.spotify_id}
          appleMusicId={artist.apple_music_id}
          previewUrl={artist.preview_url}
          spotifyEntity="artist"
        />
        <div className="flex flex-row gap-3 lg:flex-col">
          {artist.spotify_url && (
            <LinkBtn href={artist.spotify_url} label="Open in Spotify ↗" />
          )}
          {artist.apple_music_url && (
            <LinkBtn href={artist.apple_music_url} label="Open in Apple Music ↗" />
          )}
          {artist.website_url && (
            <LinkBtn href={artist.website_url} label="Official site ↗" subtle />
          )}
        </div>
      </div>
    </section>
  );
}

function LinkBtn({
  href,
  label,
  subtle,
}: {
  href: string;
  label: string;
  subtle?: boolean;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className={
        "whitespace-nowrap rounded-full px-5 py-3 text-label font-semibold uppercase tracking-wide transition-colors " +
        (subtle
          ? "border border-white/20 text-white/80 hover:text-white"
          : "bg-accent text-black hover:bg-accent-light")
      }
    >
      {label}
    </a>
  );
}
