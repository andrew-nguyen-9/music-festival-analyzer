// POST /api/recommendations { artistIds: string[] } → recommended artists (v3.7).
// Drives the "For You" home section from the user's device-local favourites,
// which only exist client-side — so the client posts the ids here and the server
// runs the aggregate neighbour query (keeps supabase-js off the client bundle).
import { NextResponse } from "next/server";
import { getRecommendedArtists } from "@/lib/recommendations";

export const runtime = "nodejs";

export async function POST(req: Request) {
  let artistIds: unknown;
  try {
    ({ artistIds } = await req.json());
  } catch {
    return NextResponse.json({ artists: [] }, { status: 400 });
  }
  if (!Array.isArray(artistIds) || artistIds.some((x) => typeof x !== "string")) {
    return NextResponse.json({ artists: [] }, { status: 400 });
  }
  if (artistIds.length === 0) return NextResponse.json({ artists: [] });
  if (artistIds.length > 200) {
    return NextResponse.json({ artists: [] }, { status: 413 });
  }
  const artists = await getRecommendedArtists(artistIds as string[]);
  return NextResponse.json({ artists });
}
