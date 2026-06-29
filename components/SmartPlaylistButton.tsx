"use client";

import { useState } from "react";
import { listFavorites } from "@/lib/favorites";
import { createPlaylistWithTracks, topTrackUrisForArtists } from "@/lib/playlist";
import { fmtDayLabel } from "@/lib/format";
import {
  isSpotifyConfigured,
  getSpotifyToken,
  loginWithSpotify,
} from "@/lib/spotify-auth";

export interface DayGroup {
  /** ISO date, or "TBD" when the festival has no day-level schedule. */
  key: string;
  artistIds: string[];
}

interface Props {
  festivalName: string;
  year: number;
  /** Lineup artist ids grouped by festival day (v2.11.2). */
  days: DayGroup[];
}

type State =
  | { kind: "idle" }
  | { kind: "working"; msg: string }
  | { kind: "done"; url: string; count: number }
  | { kind: "error"; msg: string };

function dayLabel(key: string): string {
  return key === "TBD" ? "this lineup" : fmtDayLabel(key);
}

/**
 * "Make my {day} playlist" (v2.11.2). Turns the artists you've starred who are
 * playing a given festival day into a real Spotify playlist in one action.
 * Scope is per-day when the festival has a day-level schedule, falling back to
 * the whole lineup otherwise. Logs in via PKCE on demand.
 */
export default function SmartPlaylistButton({
  festivalName,
  year,
  days,
}: Props) {
  const realDays = days.filter((d) => d.key !== "TBD");
  const perDay = realDays.length >= 2;
  const [selected, setSelected] = useState<string>(
    (perDay ? realDays[0]?.key : days[0]?.key) ?? "TBD",
  );
  const [state, setState] = useState<State>({ kind: "idle" });

  if (!isSpotifyConfigured()) {
    return (
      <p className="text-label text-white/40">
        Spotify playlists aren’t configured for this deployment yet.
      </p>
    );
  }

  // Artists in scope: the selected day (per-day mode) or the whole lineup.
  const activeIds = perDay
    ? days.find((d) => d.key === selected)?.artistIds ?? []
    : days.flatMap((d) => d.artistIds);

  const scopeLabel = perDay ? dayLabel(selected) : festivalName;
  const playlistName = perDay
    ? `${festivalName} — ${dayLabel(selected)}`
    : `${festivalName} ${year} — My Picks`;
  const playlistDesc = perDay
    ? `Your starred ${festivalName} artists playing ${dayLabel(selected)}, via Soundcheck.`
    : `Your starred ${festivalName} artists, via Soundcheck.`;

  async function run() {
    setState({ kind: "working", msg: "Gathering your starred artists…" });
    try {
      const favs = await listFavorites();
      const inScope = favs.filter((f) => activeIds.includes(f.id));
      if (inScope.length === 0) {
        setState({
          kind: "error",
          msg: `Star a few artists playing ${scopeLabel} first, then try again.`,
        });
        return;
      }

      // Resolve internal ids → matched Spotify artist ids (server cache read).
      setState({ kind: "working", msg: "Matching your artists on Spotify…" });
      const res = await fetch("/api/playlist-tracks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ artistIds: inScope.map((f) => f.id) }),
      });
      const { spotifyIds } = (await res.json()) as { spotifyIds: string[] };
      if (!spotifyIds || spotifyIds.length === 0) {
        setState({
          kind: "error",
          msg: "Your starred artists aren’t matched on Spotify yet.",
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

      // Top tracks via the user token (the app token is 403'd from top-tracks).
      setState({ kind: "working", msg: "Finding top tracks…" });
      const uris = await topTrackUrisForArtists(token, spotifyIds);
      if (uris.length === 0) {
        setState({
          kind: "error",
          msg: "Couldn’t load tracks for those artists — try again.",
        });
        return;
      }

      setState({ kind: "working", msg: "Creating your playlist…" });
      const { url, trackCount } = await createPlaylistWithTracks(
        token,
        playlistName,
        playlistDesc,
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
    <div className="flex flex-col items-start gap-3">
      {perDay && (
        <div className="flex flex-wrap gap-2">
          {realDays.map((d) => (
            <button
              key={d.key}
              onClick={() => {
                setSelected(d.key);
                setState({ kind: "idle" });
              }}
              className={`rounded-full px-4 py-1.5 text-label font-semibold transition-all ${
                selected === d.key
                  ? "bg-accent text-black"
                  : "border border-white/20 text-white/60 hover:border-white/40 hover:text-white"
              }`}
            >
              {dayLabel(d.key)}
            </button>
          ))}
        </div>
      )}
      <button
        onClick={run}
        disabled={state.kind === "working"}
        className="inline-flex items-center gap-2 rounded-full bg-[#1DB954] px-6 py-3 text-label font-semibold uppercase tracking-wide text-black transition-transform hover:scale-[1.02] disabled:opacity-60"
      >
        {state.kind === "working"
          ? state.msg
          : `Make my ${perDay ? dayLabel(selected) : festivalName} playlist`}
      </button>
      {state.kind === "error" && (
        <p className="text-label text-amber-400">{state.msg}</p>
      )}
    </div>
  );
}
