"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { CSSProperties, ReactNode } from "react";

interface RevealProps {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  /** Stagger delay in seconds. */
  delay?: number;
  /** Slide distance in px (vertical). */
  y?: number;
  once?: boolean;
}

/**
 * Scroll-into-view fade + slide. Respects prefers-reduced-motion:
 * when reduced, content renders immediately with no transform.
 */
export default function Reveal({
  children,
  className,
  style,
  delay = 0,
  y = 16,
  once = true,
}: RevealProps) {
  const reduce = useReducedMotion();

  if (reduce) {
    return (
      <div className={className} style={style}>
        {children}
      </div>
    );
  }

  return (
    <motion.div
      className={className}
      style={style}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once, margin: "0px 0px -10% 0px" }}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
