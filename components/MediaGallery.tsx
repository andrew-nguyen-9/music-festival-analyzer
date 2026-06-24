import Image from "next/image";
import Reveal from "./Reveal";
import EmptyState from "./EmptyState";
import type { Media } from "@/lib/types";

interface Props {
  media: Media[];
}

export default function MediaGallery({ media }: Props) {
  return (
    <section className="mx-auto max-w-wide px-5 py-16 md:px-8">
      <Reveal>
        <h2 className="mb-8 text-display-lg text-white">Gallery</h2>
      </Reveal>

      {media.length === 0 ? (
        <EmptyState
          title="No photos yet"
          hint="Run the Unsplash media fetcher (pipeline/media_fetcher.py) to populate this gallery. Photographer credit renders automatically."
        />
      ) : (
        <div className="columns-2 gap-3 md:columns-3 lg:columns-4 [&>*]:mb-3">
          {media.map((m) => {
            const src = m.url_regular ?? m.url_thumb ?? m.url_full;
            if (!src) return null;
            return (
              <figure
                key={m.id}
                className="break-inside-avoid overflow-hidden rounded-xl border border-white/10"
              >
                <div className="relative w-full">
                  <Image
                    src={src}
                    alt={m.alt_text ?? "Festival photo"}
                    width={600}
                    height={800}
                    sizes="(max-width: 768px) 50vw, 25vw"
                    className="h-auto w-full object-cover"
                  />
                </div>
                {m.photographer && (
                  <figcaption className="px-3 py-2 text-[11px] text-[color:var(--text-muted)]">
                    Photo by{" "}
                    {m.photographer_url ? (
                      <a
                        href={m.photographer_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-white/80 hover:text-white"
                      >
                        {m.photographer}
                      </a>
                    ) : (
                      <span className="text-white/80">{m.photographer}</span>
                    )}{" "}
                    on Unsplash
                  </figcaption>
                )}
              </figure>
            );
          })}
        </div>
      )}
    </section>
  );
}
