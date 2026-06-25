// ─────────────────────────────────────────────────────────────
// Create a Spotify playlist from track URIs (v2.9.3). Uses a user token from
// the PKCE flow (lib/spotify-auth). Track add accepts up to 100 URIs per
// request, so a typical festival playlist is a single batched request.
// ─────────────────────────────────────────────────────────────

const API = "https://api.spotify.com/v1";

async function api<T>(
  path: string,
  token: string,
  method: "GET" | "POST" = "GET",
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`Spotify ${method} ${path} → ${res.status}`);
  return (await res.json()) as T;
}

export interface CreatedPlaylist {
  url: string; // open-in-Spotify link
  trackCount: number;
}

/** Create a private playlist in the user's library and add the given URIs. */
export async function createPlaylistWithTracks(
  token: string,
  name: string,
  description: string,
  uris: string[],
): Promise<CreatedPlaylist> {
  if (uris.length === 0) throw new Error("No tracks to add");
  const me = await api<{ id: string }>("/me", token);
  const playlist = await api<{
    id: string;
    external_urls: { spotify: string };
  }>(`/users/${me.id}/playlists`, token, "POST", {
    name,
    description,
    public: false,
  });

  for (let i = 0; i < uris.length; i += 100) {
    await api(`/playlists/${playlist.id}/tracks`, token, "POST", {
      uris: uris.slice(i, i + 100),
    });
  }
  return { url: playlist.external_urls.spotify, trackCount: uris.length };
}
