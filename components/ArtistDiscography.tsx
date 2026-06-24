"use client";

import { useState } from "react";

interface Props {
  spotifyId: string;
  artistName: string;
}

export default function ArtistDiscography({ spotifyId, artistName }: Props) {
  const [showAll, setShowAll] = useState(false);

  const embedBase = `https://open.spotify.com/embed/artist/${spotifyId}?utm_source=generator&theme=0`;

  return (
    <>
      {/* Top Songs — Spotify artist embed shows top tracks automatically */}
      <section className="mx-auto max-w-wide px-5 py-12 md:px-8">
        <h2 className="mb-2 text-display-lg text-white">Top Songs</h2>
        <p className="mb-6 text-label uppercase tracking-widest text-white/40">
          Most listened · via Spotify
        </p>
        <div className="overflow-hidden rounded-2xl border border-white/10">
          <iframe
            src={embedBase}
            width="100%"
            height="380"
            allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
            loading="lazy"
            className="block"
            title={`${artistName} on Spotify`}
          />
        </div>
      </section>

      {/* Albums section */}
      <section className="mx-auto max-w-wide px-5 pb-12 md:px-8">
        <div className="mb-6 flex items-end justify-between">
          <div>
            <h2 className="text-display-lg text-white">Albums</h2>
            <p className="mt-1 text-label uppercase tracking-widest text-white/40">
              Latest releases
            </p>
          </div>
          <a
            href={`https://open.spotify.com/artist/${spotifyId}`}
            target="_blank"
            rel="noreferrer"
            className="rounded-full border border-white/20 px-4 py-2 text-label text-white/60 transition-colors hover:border-white/40 hover:text-white"
          >
            View all on Spotify ↗
          </a>
        </div>

        {/* Discography embed (shows albums list) */}
        <div className="overflow-hidden rounded-2xl border border-white/10">
          <iframe
            src={`${embedBase}&type=album`}
            width="100%"
            height={showAll ? 600 : 380}
            allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
            loading="lazy"
            className="block transition-all duration-300"
            title={`${artistName} albums on Spotify`}
          />
        </div>
        <button
          onClick={() => setShowAll((v) => !v)}
          className="mt-4 text-label text-white/40 transition-colors hover:text-white/70"
        >
          {showAll ? "Show less" : "See more albums"}
        </button>
      </section>
    </>
  );
}
