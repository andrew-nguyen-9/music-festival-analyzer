"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  previewUrl: string;
  /** Accessible label, e.g. the track or artist name. */
  label: string;
  className?: string;
}

// ponytail: module-level "currently playing" so a new play pauses the previous
// one. One global is enough for a page with a handful of players; revisit only
// if we ever need independent concurrent playback.
let current: HTMLAudioElement | null = null;

/**
 * 30s audio micro-player for Spotify preview snippets (v2.4.3). Hover/long-press
 * wiring lands in v2.6; this is the self-contained play/pause primitive both use.
 * Renders nothing useful without a previewUrl — callers gate on it.
 */
export default function PreviewPlayer({ previewUrl, label, className }: Props) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    const audio = new Audio(previewUrl);
    audio.preload = "none";
    audioRef.current = audio;
    const onEnd = () => setPlaying(false);
    audio.addEventListener("ended", onEnd);
    audio.addEventListener("pause", onEnd);
    return () => {
      audio.removeEventListener("ended", onEnd);
      audio.removeEventListener("pause", onEnd);
      audio.pause();
      if (current === audio) current = null;
    };
  }, [previewUrl]);

  function toggle() {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
      return;
    }
    if (current && current !== audio) current.pause();
    current = audio;
    void audio.play().then(() => setPlaying(true)).catch(() => setPlaying(false));
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={playing}
      aria-label={`${playing ? "Pause" : "Play"} 30-second preview of ${label}`}
      className={
        "inline-flex h-11 w-11 items-center justify-center rounded-full bg-accent text-black transition-transform hover:scale-105 active:scale-95 " +
        (className ?? "")
      }
    >
      {playing ? <PauseIcon /> : <PlayIcon />}
    </button>
  );
}

function PlayIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}
function PauseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M6 5h4v14H6zM14 5h4v14h-4z" />
    </svg>
  );
}
