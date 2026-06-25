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
  const uris = await getTopTrackUris(artistIds as string[]);
  return NextResponse.json({ uris });
}
