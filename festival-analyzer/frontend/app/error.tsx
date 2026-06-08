"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surface the full error in the browser console too.
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto flex min-h-[80vh] max-w-2xl flex-col items-center justify-center px-5 text-center">
      <p className="text-label uppercase tracking-[0.2em] text-accent">
        Something went wrong
      </p>
      <h1 className="mt-3 text-heading font-semibold text-white">
        This page hit an error while rendering
      </h1>
      <pre className="mt-5 max-w-full overflow-auto rounded-xl border border-white/15 bg-surface-elevated p-4 text-left text-[13px] leading-relaxed text-red-300">
        {error?.message || "Unknown error"}
        {error?.digest ? `\n\ndigest: ${error.digest}` : ""}
      </pre>
      <button
        onClick={reset}
        className="mt-6 rounded-full bg-accent px-6 py-3 text-label font-semibold uppercase tracking-wide text-black transition-transform hover:scale-105"
      >
        Try again
      </button>
    </div>
  );
}
