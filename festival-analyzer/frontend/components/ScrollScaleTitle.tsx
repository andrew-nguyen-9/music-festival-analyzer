"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform, useReducedMotion } from "framer-motion";

interface Props {
  name: string;
  className?: string;
}

/**
 * Festival name that scales down + fades + drifts as the hero scrolls away
 * (creative-dev scroll choreography). Reduced-motion renders it static.
 */
export default function ScrollScaleTitle({ name, className }: Props) {
  const ref = useRef<HTMLHeadingElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start 18%", "end start"],
  });

  const scale = useTransform(scrollYProgress, [0, 1], [1, 0.72]);
  const opacity = useTransform(scrollYProgress, [0, 0.85], [1, 0]);
  const y = useTransform(scrollYProgress, [0, 1], [0, -40]);

  if (reduce) {
    return (
      <h1 ref={ref} className={className}>
        {name}
      </h1>
    );
  }

  return (
    <motion.h1
      ref={ref}
      className={className}
      style={{ scale, opacity, y, transformOrigin: "left bottom" }}
    >
      {name}
    </motion.h1>
  );
}
