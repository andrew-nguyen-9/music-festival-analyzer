"use client";

import { useRef } from "react";
import { motion, useReducedMotion } from "framer-motion";

interface Note {
  glyph: string;
  color: string;
  size: number; // rem
  top: string;
  left: string;
  rotate: number;
}

// Scattered music glyphs in the festival palette.
const NOTES: Note[] = [
  { glyph: "♪", color: "#FF4500", size: 5.5, top: "18%", left: "16%", rotate: -12 },
  { glyph: "♫", color: "#00D4FF", size: 7, top: "30%", left: "70%", rotate: 8 },
  { glyph: "♩", color: "#7B2FBE", size: 4.5, top: "60%", left: "24%", rotate: 14 },
  { glyph: "♬", color: "#00A878", size: 6.5, top: "66%", left: "62%", rotate: -8 },
  { glyph: "𝄞", color: "#FF007F", size: 8, top: "12%", left: "46%", rotate: 4 },
  { glyph: "♭", color: "#E63946", size: 4, top: "48%", left: "84%", rotate: -18 },
  { glyph: "♯", color: "#FF7A45", size: 4, top: "78%", left: "40%", rotate: 10 },
];

/**
 * Playful 404 centerpiece: music glyphs you can fling around the viewport.
 * framer-motion drag with momentum + elastic constraints. Reduced-motion
 * renders them static (still visible, just not draggable-with-inertia).
 */
export default function DraggableNotes() {
  const containerRef = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();

  return (
    <div ref={containerRef} className="absolute inset-0 overflow-hidden">
      {NOTES.map((n, i) => (
        <motion.span
          key={i}
          drag
          dragConstraints={containerRef}
          dragElastic={0.4}
          dragMomentum={!reduce}
          whileDrag={{ scale: 1.25, zIndex: 50 }}
          whileHover={{ scale: 1.1 }}
          initial={{ opacity: 0, scale: 0.4 }}
          animate={{
            opacity: 1,
            scale: 1,
            rotate: n.rotate,
            ...(reduce
              ? {}
              : { y: [0, -14, 0] }),
          }}
          transition={{
            opacity: { duration: 0.5, delay: 0.1 * i },
            scale: { type: "spring", stiffness: 220, damping: 14, delay: 0.1 * i },
            y: {
              duration: 3 + i * 0.4,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 0.1 * i,
            },
          }}
          className="absolute cursor-grab select-none active:cursor-grabbing"
          style={{
            top: n.top,
            left: n.left,
            color: n.color,
            fontSize: `${n.size}rem`,
            lineHeight: 1,
            textShadow: `0 8px 40px ${n.color}55`,
            touchAction: "none",
          }}
          aria-hidden
        >
          {n.glyph}
        </motion.span>
      ))}
    </div>
  );
}
