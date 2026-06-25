import { NextResponse } from "next/server";
import { getTopTrackUris } from "@/lib/queries";

// Server-side cache read for the smart-playlist flow (v2.9). Keeps
// @supabase/supabase-js out of the client bundle — the button fetches this.
export async function POST(req: Request) {
  let artistIds: unknown;
  try {
    ({ artistIds } = await req.json());
  } catch {
    return NextResponse.json({ uris: [] }, { status: 400 });
  }
  if (!Array.isArray(artistIds) || artistIds.some((x) => typeof x !== "string")) {
    return NextResponse.json({ uris: [] }, { status: 400 });
  }
  // Bound the public IN-clause: 200 covers any real lineup (Lolla 2026 ≈ 191),
  // the button only sends a day's worth of favorites (bug_014).
  if (artistIds.length > 200) {
    return NextResponse.json({ uris: [] }, { status: 413 });
  }
  const uris = await getTopTrackUris(artistIds as string[]);
  return NextResponse.json({ uris });
}
