// ─────────────────────────────────────────────────────────────
// Supabase client (public / anon, read-only).
//
// Resilient by design: if env vars are absent (e.g. before keys are
// provisioned), `getSupabase()` returns null and every query helper in
// queries.ts degrades to empty results instead of throwing. This lets the
// whole app build and render empty states with no backend, and go live the
// instant NEXT_PUBLIC_SUPABASE_* are set.
// ─────────────────────────────────────────────────────────────

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

let client: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient | null {
  if (client) return client;
  if (!url || !anonKey) {
    if (process.env.NODE_ENV !== "production") {
      // One-time hint during local dev; not an error.
      console.warn(
        "[supabase] NEXT_PUBLIC_SUPABASE_URL / _ANON_KEY not set — " +
          "running in offline mode (empty data, empty states).",
      );
    }
    return null;
  }
  client = createClient(url, anonKey, {
    auth: { persistSession: false },
  });
  return client;
}

/** True when keys are configured and live data is expected. */
export function isSupabaseConfigured(): boolean {
  return Boolean(url && anonKey);
}
