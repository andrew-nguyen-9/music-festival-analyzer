import Portrait from "./Portrait";
import PreviewPlayer from "./PreviewPlayer";
import FavoriteButton from "./FavoriteButton";
import { formatCount } from "@/lib/format";
import type { Artist } from "@/lib/types";

interface Props {
  artist: Artist;
}

export default function ArtistHero({ artist }: Props) {
  const img = artist.header_image_url ?? artist.image_url;
  return (
    <section className="mx-auto w-full max-w-wide px-5 pb-8 pt-24 md:px-8 md:pt-32">
      <div className="flex flex-col gap-8 md:flex-row md:items-end md:gap-10">
        {/* Square portrait — the artist as a bounded subject, not a backdrop (v2.11.1). */}
        <div className="relative aspect-square w-full max-w-[340px] shrink-0 overflow-hidden rounded-2xl border border-white/10 bg-surface-elevated">
          <Portrait
            src={img}
            alt={artist.name}
            focal="50% 25%"
            sizes="(max-width: 768px) 100vw, 340px"
            priority
            scrim={false}
            vtName="vt-portrait"
          />
        </div>

        <div className="min-w-0 flex-1 pb-1">
          {artist.genres?.length > 0 && (
            <p className="mb-3 text-label uppercase tracking-[0.2em] text-white/70">
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

          <div className="mt-6">
            <FavoriteButton id={artist.id} slug={artist.slug} name={artist.name} />
          </div>
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
