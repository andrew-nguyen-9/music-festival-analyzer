// ─────────────────────────────────────────────────────────────
// Supabase Auth seam (v3.4 accounts + v3.5 Spotify sign-in).
//
// Scaffold: a browser auth client + the sign-in/out/identity calls the UI will
// use. Empty-safe — with no keys it returns null/no-ops so the app still builds
// and renders signed-out. Server-side session reads (cookies) need @supabase/ssr
// and are intentionally deferred to the UI-wiring task (see the v3.4 scaffold doc).
// ─────────────────────────────────────────────────────────────
import { createClient, type SupabaseClient, type User } from "@supabase/supabase-js";

let browserClient: SupabaseClient | null = null;

/** Browser auth client (persists the session) — null when keys are absent. */
export function getAuthClient(): SupabaseClient | null {
  if (browserClient) return browserClient;
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return null;
  browserClient = createClient(url, key, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
  });
  return browserClient;
}

export async function getCurrentUser(): Promise<User | null> {
  const sb = getAuthClient();
  if (!sb) return null;
  const { data } = await sb.auth.getUser();
  return data.user ?? null;
}

/** Spotify OAuth — doubles as account creation + the v3.5 Spotify connection. */
export async function signInWithSpotify(redirectTo?: string): Promise<void> {
  const sb = getAuthClient();
  if (!sb) return;
  await sb.auth.signInWithOAuth({
    provider: "spotify",
    options: {
      redirectTo,
      scopes: "user-top-read user-read-email playlist-modify-public playlist-modify-private",
    },
  });
}

/** Passwordless email (magic link) sign-in. */
export async function signInWithEmail(email: string, redirectTo?: string): Promise<void> {
  const sb = getAuthClient();
  if (!sb) return;
  await sb.auth.signInWithOtp({ email, options: { emailRedirectTo: redirectTo } });
}

export async function signOut(): Promise<void> {
  await getAuthClient()?.auth.signOut();
}
