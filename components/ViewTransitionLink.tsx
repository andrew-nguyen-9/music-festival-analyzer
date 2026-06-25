"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef } from "react";
import type { ComponentProps } from "react";

/** Shared name the morph target uses on both ends (the artist hero sets the same
 *  name via Portrait's `vtName`). Applied to the clicked card only at click time,
 *  so no two elements ever hold it simultaneously. */
const MORPH_NAME = "vt-portrait";

type Props = ComponentProps<typeof Link> & {
  /** Opt in to the grid→detail morph for this link's portrait. */
  morph?: boolean;
};

/**
 * next/link + a feature-detected View Transition (v2.6.2). On a plain
 * left-click, when the browser supports `startViewTransition` and the user
 * hasn't asked for reduced motion, it animates the navigation; otherwise it
 * falls back to a normal Link click (which is already viewport-prefetched, so
 * navigation is instant either way). Never produces a broken state.
 */
export default function ViewTransitionLink({ morph, onClick, ...rest }: Props) {
  const router = useRouter();
  const ref = useRef<HTMLAnchorElement>(null);

  function handle(e: React.MouseEvent<HTMLAnchorElement>) {
    onClick?.(e);
    if (e.defaultPrevented) return;

    const doc = document as Document & {
      startViewTransition?: (cb: () => void) => { finished: Promise<unknown> };
    };
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const plainClick =
      e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey;

    if (!morph || reduce || !plainClick || typeof doc.startViewTransition !== "function") {
      return; // let Link navigate normally
    }

    e.preventDefault();
    const el = ref.current;
    const href = String(rest.href);
    if (el) el.style.viewTransitionName = MORPH_NAME;
    const transition = doc.startViewTransition(() => {
      router.push(href);
    });
    void transition.finished.finally(() => {
      if (el) el.style.viewTransitionName = "";
    });
  }

  return <Link ref={ref} onClick={handle} {...rest} />;
}
