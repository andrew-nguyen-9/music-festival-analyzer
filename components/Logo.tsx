/**
 * Soundcheck brand mark — cycling loop cradling an audio waveform.
 * Geometry imported from the claude.ai/design Soundcheck Logo source.
 *
 * The mark keeps its fixed orange→yellow brand gradient even on themed
 * festival pages — brand identity stays constant, it does not reskin per
 * festival accent (that's deliberate, not a missed `var(--accent)`).
 */
type LogoProps = {
  /** Render the "Soundcheck" wordmark next to the mark. */
  withWordmark?: boolean;
  /** Tailwind classes for the icon (set height; width auto). */
  className?: string;
};

export default function Logo({ withWordmark = true, className = "h-7 w-auto" }: LogoProps) {
  return (
    <span className="inline-flex items-center gap-2">
      <svg viewBox="0 0 180 180" className={className} role="img" aria-label="Soundcheck">
        <defs>
          <linearGradient id="sc-mark" gradientUnits="userSpaceOnUse" x1="18" y1="96" x2="162" y2="84">
            <stop offset="0" stopColor="#FF6A1A" />
            <stop offset="0.52" stopColor="#FBA621" />
            <stop offset="1" stopColor="#F2D62B" />
          </linearGradient>
        </defs>
        <path d="M 30 92 C 32 56 64 38 98 38 C 128 38 150 52 152 78" fill="none" stroke="url(#sc-mark)" strokeWidth="16" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M 150 88 C 148 124 116 142 82 142 C 52 142 30 128 28 102" fill="none" stroke="url(#sc-mark)" strokeWidth="16" strokeLinecap="round" strokeLinejoin="round" />
        <polygon points="150,75 172,88 150,101" fill="url(#sc-mark)" />
        <polygon points="30,105 8,92 30,79" fill="url(#sc-mark)" />
        <g fill="url(#sc-mark)">
          <rect x="55.5" y="72" width="5" height="36" rx="2.5" />
          <rect x="63.5" y="62" width="5" height="56" rx="2.5" />
          <rect x="71.5" y="76" width="5" height="28" rx="2.5" />
          <rect x="79.5" y="57" width="5" height="66" rx="2.5" />
          <rect x="87.5" y="65" width="5" height="50" rx="2.5" />
          <rect x="95.5" y="54" width="5" height="72" rx="2.5" />
          <rect x="103.5" y="74" width="5" height="32" rx="2.5" />
          <rect x="111.5" y="63" width="5" height="54" rx="2.5" />
          <rect x="119.5" y="70" width="5" height="40" rx="2.5" />
        </g>
      </svg>
      {withWordmark && (
        <span className="font-display text-lg font-bold uppercase tracking-[0.06em] text-white">
          Soundcheck
        </span>
      )}
    </span>
  );
}
