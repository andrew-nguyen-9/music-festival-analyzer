import { NextResponse } from "next/server";
import { getArtistSpotifyIds } from "@/lib/queries";

// Resolve internal artist ids → matched Spotify artist ids for the smart-playlist
// flow (v2.9). Keeps @supabase/supabase-js out of the client bundle. Top tracks
// are fetched client-side with the user's PKCE token (the app token is 403'd
// from /artists/top-tracks), so this only returns Spotify ids.
export async function POST(req: Request) {
  let artistIds: unknown;
  try {
    ({ artistIds } = await req.json());
  } catch {
    return NextResponse.json({ spotifyIds: [] }, { status: 400 });
  }
  if (!Array.isArray(artistIds) || artistIds.some((x) => typeof x !== "string")) {
    return NextResponse.json({ spotifyIds: [] }, { status: 400 });
  }
  // Bound the public IN-clause: 200 covers any real lineup (Lolla 2026 ≈ 191),
  // the button only sends a day's worth of favorites (bug_014).
  if (artistIds.length > 200) {
    return NextResponse.json({ spotifyIds: [] }, { status: 413 });
  }
  const spotifyIds = await getArtistSpotifyIds(artistIds as string[]);
  return NextResponse.json({ spotifyIds });
}
