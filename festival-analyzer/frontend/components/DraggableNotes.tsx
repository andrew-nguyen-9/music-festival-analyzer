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

// ♫ and ♩ only — matches the visual simplicity of the app's typography.
const NOTES: Note[] = [
  { glyph: "♫", color: "#FF4500", size: 7,   top: "8%",  left: "12%", rotate: -12 },
  { glyph: "♩", color: "#8B5CF6", size: 4.5, top: "14%", left: "38%", rotate: 8  },
  { glyph: "♫", color: "#00D4FF", size: 6,   top: "10%", left: "62%", rotate: -6 },
  { glyph: "♩", color: "#FF7A45", size: 5,   top: "22%", left: "82%", rotate: 14 },
  { glyph: "♫", color: "#00A878", size: 8,   top: "32%", left: "6%",  rotate: 4  },
  { glyph: "♩", color: "#FF007F", size: 3.5, top: "38%", left: "52%", rotate: -16 },
  { glyph: "♫", color: "#A78BFA", size: 5.5, top: "44%", left: "74%", rotate: 10 },
  { glyph: "♩", color: "#FF4500", size: 6.5, top: "54%", left: "28%", rotate: -8 },
  { glyph: "♫", color: "#00D4FF", size: 4,   top: "58%", left: "88%", rotate: 6  },
  { glyph: "♩", color: "#8B5CF6", size: 7,   top: "66%", left: "16%", rotate: -14 },
  { glyph: "♫", color: "#FF7A45", size: 4.5, top: "70%", left: "46%", rotate: 18 },
  { glyph: "♩", color: "#00A878", size: 5,   top: "76%", left: "68%", rotate: -4 },
  { glyph: "♫", color: "#FF007F", size: 6,   top: "82%", left: "8%",  rotate: 10 },
  { glyph: "♩", color: "#A78BFA", size: 3.5, top: "86%", left: "34%", rotate: -20 },
  { glyph: "♫", color: "#FF4500", size: 5,   top: "90%", left: "78%", rotate: 8  },
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
