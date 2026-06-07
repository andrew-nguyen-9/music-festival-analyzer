"use client";

import { useEffect, useState } from "react";

interface Props {
  spotifyId: string | null;
  appleMusicId: string | null;
  previewUrl: string | null;
  /** "artist" | "track" — Spotify embed entity type. */
  spotifyEntity?: "artist" | "track";
}

type Service = "spotify" | "apple";
const STORAGE_KEY = "fa:music-service";

const appleConfigured = Boolean(
  process.env.NEXT_PUBLIC_APPLE_MUSIC_DEV_TOKEN,
);

/**
 * Spotify / Apple Music switch. Spotify renders an auth-free embed iframe.
 * Apple Music is gated behind NEXT_PUBLIC_APPLE_MUSIC_DEV_TOKEN — when the
 * token is absent it shows a graceful "not configured" panel. Falls back to
 * a native <audio> 30s preview when no streaming embed is available.
 * User's choice persists to localStorage.
 */
export default function MusicPlayerToggle({
  spotifyId,
  appleMusicId,
  previewUrl,
  spotifyEntity = "artist",
}: Props) {
  const [service, setService] = useState<Service>("spotify");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY) as Service | null;
    if (saved === "spotify" || saved === "apple") setService(saved);
    setReady(true);
  }, []);

  function choose(s: Service) {
    setService(s);
    window.localStorage.setItem(STORAGE_KEY, s);
  }

  const hasSpotify = Boolean(spotifyId);
  const hasApple = Boolean(appleMusicId);

  // Nothing to play at all.
  if (!hasSpotify && !hasApple && !previewUrl) {
    return (
      <div className="rounded-xl border border-white/10 bg-surface-elevated p-5 text-body text-[color:var(--text-muted)]">
        No streaming links available for this artist yet.
      </div>
    );
  }

  const active: Service = service === "apple" && hasApple ? "apple" : "spotify";

  return (
    <div className="rounded-2xl border border-white/10 bg-surface-elevated p-4">
      <div className="mb-4 inline-flex rounded-full border border-white/15 p-1">
        <ToggleBtn
          label="Spotify"
          active={active === "spotify"}
          onClick={() => choose("spotify")}
        />
        <ToggleBtn
          label="Apple Music"
          active={active === "apple"}
          onClick={() => choose("apple")}
        />
      </div>

      {!ready ? (
        <div className="h-[152px] animate-pulse rounded-xl bg-white/5" />
      ) : active === "spotify" ? (
        hasSpotify ? (
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
        ) : (
          <PreviewFallback previewUrl={previewUrl} />
        )
      ) : appleConfigured && hasApple ? (
        <iframe
          title="Apple Music player"
          src={`https://embed.music.apple.com/us/artist/${appleMusicId}`}
          width="100%"
          height="352"
          loading="lazy"
          allow="autoplay *; encrypted-media *;"
          className="rounded-xl"
          style={{ border: 0 }}
        />
      ) : (
        <div className="flex h-[140px] flex-col items-center justify-center rounded-xl border border-dashed border-white/15 px-6 text-center text-body text-[color:var(--text-muted)]">
          <p className="font-semibold text-white">Apple Music coming soon</p>
          <p className="mt-1 text-label">
            {hasApple
              ? "Set NEXT_PUBLIC_APPLE_MUSIC_DEV_TOKEN to enable the Apple Music player."
              : "No Apple Music link for this artist yet."}
          </p>
        </div>
      )}
    </div>
  );
}

function ToggleBtn({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={
        "rounded-full px-4 py-1.5 text-label font-semibold uppercase tracking-wide transition-colors " +
        (active ? "bg-accent text-black" : "text-white/70 hover:text-white")
      }
    >
      {label}
    </button>
  );
}

function PreviewFallback({ previewUrl }: { previewUrl: string | null }) {
  if (!previewUrl) {
    return (
      <div className="flex h-[140px] items-center justify-center rounded-xl border border-dashed border-white/15 text-body text-[color:var(--text-muted)]">
        No Spotify embed available.
      </div>
    );
  }
  return (
    <div className="rounded-xl bg-black/30 p-4">
      <p className="mb-2 text-label uppercase tracking-wide text-white/60">
        30-second preview
      </p>
      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <audio controls src={previewUrl} className="w-full" />
    </div>
  );
}
