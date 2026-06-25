"use client";

import { useState } from "react";
import { listFavorites } from "@/lib/favorites";
import { createPlaylistWithTracks } from "@/lib/playlist";
import {
  isSpotifyConfigured,
  getSpotifyToken,
  loginWithSpotify,
} from "@/lib/spotify-auth";

interface Props {
  festivalName: string;
  year: number;
  /** Artist ids in this festival's lineup — favorites are intersected with these. */
  lineupArtistIds: string[];
}

type State =
  | { kind: "idle" }
  | { kind: "working"; msg: string }
  | { kind: "done"; url: string; count: number }
  | { kind: "error"; msg: string };

/**
 * "Make my {festival} playlist" (v2.9.4). Turns the artists you've starred who
 * are playing this festival into a real Spotify playlist in one action. Scope is
 * per-festival (the chosen default). Logs in via PKCE on demand.
 */
export default function SmartPlaylistButton({
  festivalName,
  year,
  lineupArtistIds,
}: Props) {
  const [state, setState] = useState<State>({ kind: "idle" });

  if (!isSpotifyConfigured()) {
    return (
      <p className="text-label text-white/40">
        Spotify playlists aren’t configured for this deployment yet.
      </p>
    );
  }

  async function run() {
    setState({ kind: "working", msg: "Gathering your starred artists…" });
    try {
      const favs = await listFavorites();
      const inLineup = favs.filter((f) => lineupArtistIds.includes(f.id));
      if (inLineup.length === 0) {
        setState({
          kind: "error",
          msg: "Star a few artists in this lineup first, then try again.",
        });
        return;
      }

      // Login on demand — bounces to Spotify and back to this page.
      if (!getSpotifyToken()) {
        await loginWithSpotify(window.location.pathname);
        return; // navigates away
      }
      const token = getSpotifyToken();
      if (!token) {
        setState({ kind: "error", msg: "Not signed in to Spotify." });
        return;
      }

      setState({ kind: "working", msg: "Finding top tracks…" });
      const res = await fetch("/api/playlist-tracks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ artistIds: inLineup.map((f) => f.id) }),
      });
      const { uris } = (await res.json()) as { uris: string[] };
      if (!uris || uris.length === 0) {
        setState({
          kind: "error",
          msg: "No cached tracks for your starred artists yet.",
        });
        return;
      }

      setState({ kind: "working", msg: "Creating your playlist…" });
      const { url, trackCount } = await createPlaylistWithTracks(
        token,
        `${festivalName} ${year} — My Picks`,
        `Your starred ${festivalName} artists, via Festival Analyzer.`,
        uris,
      );
      setState({ kind: "done", url, count: trackCount });
    } catch (e) {
      setState({ kind: "error", msg: (e as Error).message });
    }
  }

  if (state.kind === "done") {
    return (
      <a
        href={state.url}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-2 rounded-full bg-[#1DB954] px-6 py-3 text-label font-semibold uppercase tracking-wide text-black transition-transform hover:scale-[1.02]"
      >
        ✓ Playlist ready ({state.count} tracks) — open in Spotify ↗
      </a>
    );
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <button
        onClick={run}
        disabled={state.kind === "working"}
        className="inline-flex items-center gap-2 rounded-full bg-[#1DB954] px-6 py-3 text-label font-semibold uppercase tracking-wide text-black transition-transform hover:scale-[1.02] disabled:opacity-60"
      >
        {state.kind === "working" ? state.msg : `Make my ${festivalName} playlist`}
      </button>
      {state.kind === "error" && (
        <p className="text-label text-amber-400">{state.msg}</p>
      )}
    </div>
  );
}
