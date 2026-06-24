"use client";

import { useEffect, useRef } from "react";

/**
 * Custom cursor — a blend-mode ring that lerps toward the pointer and grows
 * over interactive elements. Only activates on fine pointers (mouse) with
 * motion allowed; touch + reduced-motion keep the native cursor untouched.
 * Native cursor is only hidden after this mounts (JS on), so no-JS users are
 * never left cursorless.
 */
export default function CustomCursor() {
  const ringRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fine = window.matchMedia("(pointer: fine)").matches;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!fine || reduce) return;

    const ring = ringRef.current;
    if (!ring) return;

    document.body.classList.add("cursor-none");
    ring.style.opacity = "1";

    let mx = window.innerWidth / 2;
    let my = window.innerHeight / 2;
    let rx = mx;
    let ry = my;
    let raf = 0;

    const onMove = (e: MouseEvent) => {
      mx = e.clientX;
      my = e.clientY;
      const interactive = (e.target as HTMLElement)?.closest(
        "a, button, input, [role='button'], [data-cursor='grow']",
      );
      ring.classList.toggle("cursor-ring--grow", Boolean(interactive));
    };

    const loop = () => {
      rx += (mx - rx) * 0.18;
      ry += (my - ry) * 0.18;
      ring.style.transform = `translate3d(${rx}px, ${ry}px, 0) translate(-50%, -50%)`;
      raf = requestAnimationFrame(loop);
    };

    window.addEventListener("mousemove", onMove);
    raf = requestAnimationFrame(loop);

    return () => {
      window.removeEventListener("mousemove", onMove);
      cancelAnimationFrame(raf);
      document.body.classList.remove("cursor-none");
    };
  }, []);

  return <div ref={ringRef} className="cursor-ring" aria-hidden />;
}
