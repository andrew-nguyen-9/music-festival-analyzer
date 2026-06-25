"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { completeSpotifyLogin } from "@/lib/spotify-auth";

export const dynamic = "force-dynamic";

/** Spotify OAuth redirect target (v2.9.1). Exchanges the code for a token, then
 *  returns the user to where they started the playlist flow. */
export default function SpotifyCallback() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const err = params.get("error");
    if (err) {
      setError(err);
      return;
    }
    if (!code) {
      setError("Missing authorization code");
      return;
    }
    completeSpotifyLogin(code)
      .then((returnTo) => router.replace(returnTo))
      .catch((e) => setError((e as Error).message));
  }, [router]);

  return (
    <section className="mx-auto max-w-md px-5 py-32 text-center">
      {error ? (
        <>
          <h1 className="text-display-md text-white">Couldn’t connect Spotify</h1>
          <p className="mt-3 text-body text-white/60">{error}</p>
        </>
      ) : (
        <p className="text-body text-white/70">Connecting your Spotify…</p>
      )}
    </section>
  );
}
