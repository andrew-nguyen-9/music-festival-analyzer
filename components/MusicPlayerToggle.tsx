"use client";

interface Props {
  spotifyId: string | null;
  previewUrl: string | null;
  /** "artist" | "track" — Spotify embed entity type. */
  spotifyEntity?: "artist" | "track";
}

/**
 * Spotify player. Renders an auth-free Spotify embed iframe when a Spotify ID
 * is available; falls back to a native <audio> 30s preview; otherwise shows a
 * tidy "no link" state. (Apple Music / X toggles were removed for v1.)
 */
export default function MusicPlayerToggle({
  spotifyId,
  previewUrl,
  spotifyEntity = "artist",
}: Props) {
  if (spotifyId) {
    return (
      <div className="rounded-2xl border border-white/10 bg-surface-elevated p-4">
        <iframe
          title="Spotify player"
          src={`https://open.spotify.com/embed/${spotifyEntity}/${spotifyId}?utm_source=festival-analyzer`}
          width="100%"
          height="352"
          loading="lazy"
          allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
          className="rounded-xl"
          style={{ border: 0 }}
        />
      </div>
    );
  }

  if (previewUrl) {
    return (
      <div className="rounded-2xl border border-white/10 bg-surface-elevated p-4">
        <p className="mb-2 text-label uppercase tracking-wide text-white/60">
          30-second preview
        </p>
        {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
        <audio controls src={previewUrl} className="w-full" />
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-surface-elevated p-5 text-body text-[color:var(--text-muted)]">
      No Spotify link available for this artist yet — run the artist enricher to
      add one.
    </div>
  );
}
