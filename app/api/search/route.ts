// GET /api/search?q=… — unified festival+artist search (v3.3).
// Server route so the anon Supabase client + RPC stay off the client bundle.
// Returns ranked results; when empty, includes "did you mean?" suggestions.
import { NextResponse } from "next/server";
import { searchAll, searchSuggest } from "@/lib/queries";

export const runtime = "nodejs";
export const revalidate = 0; // always fresh; the query itself is cheap + indexed

export async function GET(request: Request) {
  const q = new URL(request.url).searchParams.get("q")?.trim() ?? "";
  if (q.length < 2) {
    return NextResponse.json({ query: q, results: [], suggestions: [] });
  }
  const results = await searchAll(q);
  const suggestions = results.length === 0 ? await searchSuggest(q) : [];
  return NextResponse.json({ query: q, results, suggestions });
}
