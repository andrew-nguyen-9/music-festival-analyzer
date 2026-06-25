// ─────────────────────────────────────────────────────────────
// Spotify user auth — Authorization Code + PKCE (v2.9.1).
//
// Public client: no client secret, so the whole flow (including the token
// exchange) runs in the browser against Spotify's CORS-enabled token endpoint.
// This is distinct from the pipeline's client-credentials sync worker (v2.2),
// which never acts on behalf of a user.
//
// Env-gated on NEXT_PUBLIC_SPOTIFY_CLIENT_ID — when unset, isConfigured() is
// false and the UI shows a "not configured" state instead of breaking.
// ─────────────────────────────────────────────────────────────

const CLIENT_ID = process.env.NEXT_PUBLIC_SPOTIFY_CLIENT_ID;
const SCOPES = "playlist-modify-public playlist-modify-private";
const TOKEN_KEY = "fa_sp_token";
const VERIFIER_KEY = "fa_sp_verifier";
const RETURN_KEY = "fa_sp_return";

export function isSpotifyConfigured(): boolean {
  return Boolean(CLIENT_ID);
}

function redirectUri(): string {
  return `${window.location.origin}/spotify/callback`;
}

function base64url(bytes: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function randomVerifier(): string {
  const arr = new Uint8Array(64);
  crypto.getRandomValues(arr);
  return base64url(arr.buffer);
}

async function challenge(verifier: string): Promise<string> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(verifier),
  );
  return base64url(digest);
}

/** Kick off login; on return Spotify lands on /spotify/callback. */
export async function loginWithSpotify(returnTo: string): Promise<void> {
  if (!CLIENT_ID) throw new Error("Spotify not configured");
  const verifier = randomVerifier();
  sessionStorage.setItem(VERIFIER_KEY, verifier);
  sessionStorage.setItem(RETURN_KEY, returnTo);
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    response_type: "code",
    redirect_uri: redirectUri(),
    scope: SCOPES,
    code_challenge_method: "S256",
    code_challenge: await challenge(verifier),
  });
  window.location.href = `https://accounts.spotify.com/authorize?${params}`;
}

/** Exchange the ?code for a token (called by the callback page). Returns the
 *  stored return-to path. */
export async function completeSpotifyLogin(code: string): Promise<string> {
  if (!CLIENT_ID) throw new Error("Spotify not configured");
  const verifier = sessionStorage.getItem(VERIFIER_KEY);
  if (!verifier) throw new Error("Missing PKCE verifier");
  const res = await fetch("https://accounts.spotify.com/api/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      code,
      redirect_uri: redirectUri(),
      client_id: CLIENT_ID,
      code_verifier: verifier,
    }),
  });
  if (!res.ok) throw new Error(`Token exchange failed (${res.status})`);
  const json = (await res.json()) as { access_token: string; expires_in: number };
  sessionStorage.setItem(
    TOKEN_KEY,
    JSON.stringify({
      token: json.access_token,
      expires: Date.now() + json.expires_in * 1000,
    }),
  );
  sessionStorage.removeItem(VERIFIER_KEY);
  // Same-origin paths only — block open-redirect via the return-to (incl.
  // protocol-relative "//host"). The callback feeds this to router.replace (bug_017).
  const stored = sessionStorage.getItem(RETURN_KEY) ?? "/";
  return stored.startsWith("/") && !stored.startsWith("//") ? stored : "/";
}

/** A non-expired access token, or null if the user must (re)authenticate. */
export function getSpotifyToken(): string | null {
  const raw =
    typeof sessionStorage !== "undefined"
      ? sessionStorage.getItem(TOKEN_KEY)
      : null;
  if (!raw) return null;
  try {
    const { token, expires } = JSON.parse(raw) as {
      token: string;
      expires: number;
    };
    return Date.now() < expires - 30_000 ? token : null;
  } catch {
    return null;
  }
}
