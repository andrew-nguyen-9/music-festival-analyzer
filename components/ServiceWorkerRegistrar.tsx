"use client";

import { useEffect } from "react";

/**
 * Registers the service worker (v2.7.2). Production only — registering in dev
 * makes Next's HMR fight a caching SW. Renders nothing.
 */
export default function ServiceWorkerRegistrar() {
  useEffect(() => {
    if (
      process.env.NODE_ENV !== "production" ||
      typeof navigator === "undefined" ||
      !("serviceWorker" in navigator)
    ) {
      return;
    }
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Registration failure is non-fatal — app still works online.
    });
  }, []);

  return null;
}
