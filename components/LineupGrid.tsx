import Reveal from "./Reveal";
import EmptyState from "./EmptyState";
import Portrait from "./Portrait";
import ViewTransitionLink from "./ViewTransitionLink";
import type { LineupEntry } from "@/lib/types";

interface Props {
  lineup: LineupEntry[];
}

/** Group lineup entries by stage, headliners first. */
function groupByStage(lineup: LineupEntry[]): [string, LineupEntry[]][] {
  const groups = new Map<string, LineupEntry[]>();
  for (const entry of lineup) {
    const key = entry.stage?.trim() || "Lineup";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(entry);
  }
  for (const list of groups.values()) {
    list.sort((a, b) => {
      if (a.is_headliner !== b.is_headliner) return a.is_headliner ? -1 : 1;
      return (b.artist.spotify_popularity ?? 0) - (a.artist.spotify_popularity ?? 0);
    });
  }
  return [...groups.entries()];
}

export default function LineupGrid({ lineup }: Props) {
  return (
    <section className="mx-auto max-w-wide px-5 py-16 md:px-8">
      <Reveal>
        <h2 className="mb-8 text-display-lg text-white">Lineup</h2>
      </Reveal>

      {lineup.length === 0 ? (
        <EmptyState
          title="Lineup coming soon"
          hint="Once the lineup rows are seeded (or the artist enricher runs), artists grouped by stage will appear here."
        />
      ) : (
        <div className="space-y-12">
          {groupByStage(lineup).map(([stage, entries]) => (
            <div key={stage}>
              <h3 className="mb-4 text-heading font-semibold text-accent">
                {stage}
              </h3>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                {entries.map((entry, i) => (
                  <Reveal key={entry.id} delay={Math.min(i * 0.04, 0.4)}>
                    <ArtistTile entry={entry} />
                  </Reveal>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function ArtistTile({ entry }: { entry: LineupEntry }) {
  const { artist } = entry;
  const img = artist.image_url ?? artist.header_image_url;
  return (
    <ViewTransitionLink
      morph
      href={`/artist/${artist.slug}`}
      className="group relative block overflow-hidden rounded-xl border border-white/10 bg-surface-elevated"
    >
      <div className="relative aspect-square w-full overflow-hidden">
        <Portrait
          src={img}
          alt={artist.name}
          sizes="(max-width: 640px) 50vw, 25vw"
          hoverZoom
          previewUrl={artist.preview_url}
        />
        {entry.is_headliner && (
          <span className="absolute left-2 top-2 rounded-full bg-accent px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-black">
            Headliner
          </span>
        )}
        <div className="absolute inset-x-0 bottom-0 p-3">
          <p
            className={
              "font-semibold leading-tight text-white " +
              (entry.is_headliner ? "text-display-md" : "text-body-lg")
            }
          >
            {artist.name}
          </p>
          {artist.genres?.length > 0 && (
            <p className="mt-0.5 truncate text-[11px] uppercase tracking-wide text-white/60">
              {artist.genres.slice(0, 2).join(" · ")}
            </p>
          )}
        </div>
      </div>
    </ViewTransitionLink>
  );
}
