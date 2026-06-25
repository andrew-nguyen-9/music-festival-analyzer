"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  previewUrl: string;
  /** Accessible label, e.g. the track or artist name. */
  label: string;
  /** "md" = 44px hero pill (default), "sm" = 32px tile affordance. */
  size?: "sm" | "md";
  className?: string;
}

// ponytail: module-level "currently playing" so a new play pauses the previous
// one. One global is enough for a page with a handful of players; revisit only
// if we ever need independent concurrent playback.
let current: HTMLAudioElement | null = null;

/**
 * 30s audio micro-player for Spotify preview snippets (v2.4 / wired into tiles in
 * v2.6). The Audio object is created lazily on first play, not on mount, so a grid
 * of these stays cheap. Callers gate on a present previewUrl.
 */
export default function PreviewPlayer({
  previewUrl,
  label,
  size = "md",
  className,
}: Props) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);

  // Tear down on unmount / url change — but never create eagerly.
  useEffect(() => {
    return () => {
      const a = audioRef.current;
      if (a) {
        a.pause();
        if (current === a) current = null;
      }
      audioRef.current = null;
    };
  }, [previewUrl]);

  function toggle(e: React.MouseEvent) {
    e.preventDefault(); // tiles wrap these in a Link — don't navigate.
    e.stopPropagation();
    let audio = audioRef.current;
    if (!audio) {
      audio = new Audio(previewUrl);
      audio.preload = "none";
      audio.addEventListener("ended", () => setPlaying(false));
      audio.addEventListener("pause", () => setPlaying(false));
      audioRef.current = audio;
    }
    if (playing) {
      audio.pause();
      return;
    }
    if (current && current !== audio) current.pause();
    current = audio;
    void audio
      .play()
      .then(() => setPlaying(true))
      .catch(() => setPlaying(false));
  }

  const dim = size === "sm" ? "h-8 w-8" : "h-11 w-11";
  const icon = size === "sm" ? 14 : 18;

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={playing}
      aria-label={`${playing ? "Pause" : "Play"} 30-second preview of ${label}`}
      className={
        `inline-flex ${dim} items-center justify-center rounded-full bg-accent text-black shadow transition-transform hover:scale-105 active:scale-95 ` +
        (className ?? "")
      }
    >
      {playing ? <PauseIcon s={icon} /> : <PlayIcon s={icon} />}
    </button>
  );
}

function PlayIcon({ s }: { s: number }) {
  return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}
function PauseIcon({ s }: { s: number }) {
  return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M6 5h4v14H6zM14 5h4v14h-4z" />
    </svg>
  );
}
