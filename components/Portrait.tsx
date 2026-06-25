import Image from "next/image";
import { accentGradient } from "@/lib/festival-theme";

interface Props {
  src?: string | null;
  alt: string;
  /** object-position focal point. Default favors faces (upper-center) so
   *  wildly different source crops don't decapitate the subject (v2.4.1). */
  focal?: string;
  sizes?: string;
  priority?: boolean;
  /** Bottom scrim so overlaid labels stay legible. */
  scrim?: boolean;
  /** Zoom on hover when the parent is a `group`. */
  hoverZoom?: boolean;
}

/**
 * Normalized artist/festival media layer (v2.4.1). Drop inside a `relative`,
 * aspect-sized box; the parent owns the aspect ratio, rounding, and any label
 * overlays. This is the single source of truth for portrait framing — replaces
 * the near-identical image+fallback+scrim block previously copied across the
 * lineup grids, so every portrait reads as one editorial treatment.
 */
export default function Portrait({
  src,
  alt,
  focal = "50% 28%",
  sizes = "(max-width: 640px) 50vw, 25vw",
  priority,
  scrim = true,
  hoverZoom,
}: Props) {
  return (
    <>
      {src ? (
        <Image
          src={src}
          alt={alt}
          fill
          priority={priority}
          sizes={sizes}
          style={{ objectPosition: focal }}
          className={
            "object-cover" +
            (hoverZoom
              ? " transition-transform duration-500 group-hover:scale-105"
              : "")
          }
        />
      ) : (
        <div
          className="grid h-full w-full place-items-center"
          style={{ backgroundImage: accentGradient(null) }}
          aria-hidden
        >
          <span className="select-none text-display-md font-bold text-white/30">
            {initials(alt)}
          </span>
        </div>
      )}
      {scrim && <div className="hero-scrim absolute inset-0 opacity-90" />}
    </>
  );
}

/** "Tame Impala" -> "TI". Empty-safe. */
function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0] ?? "")
    .join("")
    .toUpperCase();
}
