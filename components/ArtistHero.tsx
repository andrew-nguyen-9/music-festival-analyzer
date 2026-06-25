import Portrait from "./Portrait";
import PreviewPlayer from "./PreviewPlayer";
import { formatCount } from "@/lib/format";
import type { Artist } from "@/lib/types";

interface Props {
  artist: Artist;
}

export default function ArtistHero({ artist }: Props) {
  const img = artist.header_image_url ?? artist.image_url;
  return (
    <section className="relative flex min-h-[70vh] flex-col justify-end overflow-hidden">
      <Portrait
        src={img}
        alt={artist.name}
        focal="50% 22%"
        sizes="100vw"
        priority
        scrim={false}
        vtName="vt-portrait"
      />
      {/* Bottom + side gradients blend the image into the page */}
      <div className="hero-scrim absolute inset-0" />
      <div className="absolute inset-y-0 left-0 w-48 bg-gradient-to-r from-black/70 to-transparent" aria-hidden />
      <div className="absolute inset-y-0 right-0 w-48 bg-gradient-to-l from-black/70 to-transparent" aria-hidden />

      <div className="relative mx-auto w-full max-w-wide px-5 pb-14 pt-32 md:px-8">
        {artist.genres?.length > 0 && (
          <p className="mb-3 text-label uppercase tracking-[0.2em] text-white/80">
            {artist.genres.slice(0, 3).join(" · ")}
          </p>
        )}
        <div className="flex flex-wrap items-end gap-x-5 gap-y-3">
          <h1 className="text-display-xl text-white">{artist.name}</h1>
          {artist.preview_url && (
            <PreviewPlayer
              previewUrl={artist.preview_url}
              label={artist.name}
              className="mb-2 shrink-0"
            />
          )}
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-6 text-white/85">
          {artist.spotify_followers != null && (
            <Stat
              value={formatCount(artist.spotify_followers)}
              label="Spotify followers"
            />
          )}
          {artist.spotify_popularity != null && (
            <Stat
              value={`${artist.spotify_popularity}`}
              label="Popularity / 100"
            />
          )}
          {(artist.origin_city || artist.origin_country) && (
            <Stat
              value={[artist.origin_city, artist.origin_country]
                .filter(Boolean)
                .join(", ")}
              label="From"
            />
          )}
        </div>
      </div>
    </section>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <p className="text-display-md font-semibold leading-none text-white">
        {value}
      </p>
      <p className="mt-1 text-label uppercase tracking-wide text-white/60">
        {label}
      </p>
    </div>
  );
}
