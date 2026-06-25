"use client";

import { useEffect, useState } from "react";

/**
 * Offline UX (v2.7.5): a quiet banner when the network drops, so cached content
 * reads as intentional rather than broken. No infinite spinners — content is
 * already server-rendered/cached; this just labels the state.
 */
export default function OfflineIndicator() {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const sync = () => setOffline(!navigator.onLine);
    sync();
    window.addEventListener("online", sync);
    window.addEventListener("offline", sync);
    return () => {
      window.removeEventListener("online", sync);
      window.removeEventListener("offline", sync);
    };
  }, []);

  if (!offline) return null;

  return (
    <div
      role="status"
      className="fixed inset-x-0 top-0 z-[80] bg-amber-500/95 px-4 py-2 text-center text-label font-semibold uppercase tracking-wide text-black"
    >
      Offline — showing saved &amp; cached data
    </div>
  );
}
