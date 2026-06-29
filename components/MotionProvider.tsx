"use client";

import { MotionConfig } from "framer-motion";
import { useEffect, useState } from "react";
import { readA11ySettings, type A11ySettings } from "@/lib/settings";

/**
 * Forces Framer Motion into reduced-motion when the a11y "reduce motion" toggle
 * is on (the CSS class only stops CSS transitions/animations, not Framer's
 * JS-driven transforms). `reducedMotion="user"` otherwise respects the OS
 * setting. Reads localStorage on mount and reacts to live changes from the panel.
 */
export default function MotionProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [reduce, setReduce] = useState(false);

  useEffect(() => {
    setReduce(readA11ySettings().motion);
    const onChange = (e: Event) =>
      setReduce((e as CustomEvent<A11ySettings>).detail.motion);
    window.addEventListener("soundcheck:a11y-changed", onChange);
    return () =>
      window.removeEventListener("soundcheck:a11y-changed", onChange);
  }, []);

  return (
    <MotionConfig reducedMotion={reduce ? "always" : "user"}>
      {children}
    </MotionConfig>
  );
}
