/* Soundcheck service worker (v2.7.2).
 * ponytail: hand-rolled stale-while-revalidate instead of Workbox — the policy
 * is small enough that a build-time toolchain isn't worth it. Two strategies:
 *   - navigations + same-origin GET → stale-while-revalidate (instant from cache,
 *     refreshed in the background), with an offline fallback to the cached shell.
 *   - everything else → network passthrough.
 * Upgrade path: if precaching/asset-revisioning gets fiddly, swap in Workbox.
 */
const CACHE = "fa-v1";
const OFFLINE_URL = "/";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.add(OFFLINE_URL)).catch(() => {}),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // don't touch Supabase/Spotify/CDN

  // Never cache the OAuth callback (the ?code lands in the cache key), API
  // responses, or any code/error redirect — pass straight to network (bug_015).
  if (
    url.pathname === "/spotify/callback" ||
    url.pathname.startsWith("/api/") ||
    url.searchParams.has("code") ||
    url.searchParams.has("error")
  ) {
    return;
  }

  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const cached = await cache.match(req);
      const network = fetch(req)
        .then((res) => {
          if (res && res.status === 200) cache.put(req, res.clone());
          return res;
        })
        .catch(() => null);

      // Stale-while-revalidate: serve cache immediately, refresh behind it.
      if (cached) {
        event.waitUntil(network);
        return cached;
      }
      const res = await network;
      if (res) return res;
      // Offline + uncached: fall back to the shell for navigations.
      if (req.mode === "navigate") {
        const shell = await cache.match(OFFLINE_URL);
        if (shell) return shell;
      }
      return new Response("Offline", { status: 503, statusText: "Offline" });
    }),
  );
});
