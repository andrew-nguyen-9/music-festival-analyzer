// ─────────────────────────────────────────────────────────────
// Runtime festival theming.
// Derives a small palette from a single accent hex (festivals.accent_color)
// per docs/UI_SPEC.md. Pure functions — safe in Server Components.
// ─────────────────────────────────────────────────────────────

export interface FestivalTheme {
  accent: string;
  accentLight: string;
  accentDark: string;
  surface: string;
  surfaceElevated: string;
  text: string;
  textMuted: string;
}

const DEFAULT_ACCENT = "#FF4500"; // Lollapalooza orange-red

function clamp(n: number, min = 0, max = 255): number {
  return Math.min(max, Math.max(min, Math.round(n)));
}

function normalizeHex(hex: string): string {
  let h = hex.trim().replace(/^#/, "");
  if (h.length === 3) {
    h = h
      .split("")
      .map((c) => c + c)
      .join("");
  }
  if (!/^[0-9a-fA-F]{6}$/.test(h)) return DEFAULT_ACCENT.replace("#", "");
  return h;
}

export function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const h = normalizeHex(hex);
  return {
    r: parseInt(h.slice(0, 2), 16),
    g: parseInt(h.slice(2, 4), 16),
    b: parseInt(h.slice(4, 6), 16),
  };
}

function rgbToHex(r: number, g: number, b: number): string {
  return (
    "#" +
    [r, g, b]
      .map((v) => clamp(v).toString(16).padStart(2, "0"))
      .join("")
  );
}

/** Lighten toward white by `amount` (0–1). */
export function lighten(hex: string, amount: number): string {
  const { r, g, b } = hexToRgb(hex);
  return rgbToHex(
    r + (255 - r) * amount,
    g + (255 - g) * amount,
    b + (255 - b) * amount,
  );
}

/** Darken toward black by `amount` (0–1). */
export function darken(hex: string, amount: number): string {
  const { r, g, b } = hexToRgb(hex);
  return rgbToHex(r * (1 - amount), g * (1 - amount), b * (1 - amount));
}

/** Build the full festival palette from a single accent hex. */
export function getFestivalTheme(accentHex?: string | null): FestivalTheme {
  const accent = accentHex && /^#?[0-9a-fA-F]{3,6}$/.test(accentHex.trim())
    ? "#" + normalizeHex(accentHex)
    : DEFAULT_ACCENT;
  return {
    accent,
    accentLight: lighten(accent, 0.3),
    accentDark: darken(accent, 0.2),
    surface: "#0A0A0A",
    surfaceElevated: "#141414",
    text: "#FFFFFF",
    textMuted: "rgba(255,255,255,0.55)",
  };
}

/** CSS custom properties for inline `style` on a theming wrapper. */
export function themeToCssVars(theme: FestivalTheme): Record<string, string> {
  return {
    "--accent": theme.accent,
    "--accent-light": theme.accentLight,
    "--accent-dark": theme.accentDark,
    "--surface": theme.surface,
    "--surface-elevated": theme.surfaceElevated,
    "--text": theme.text,
    "--text-muted": theme.textMuted,
  };
}

/**
 * A deterministic CSS gradient derived from the accent, used as a
 * placeholder when a festival/artist has no hero image yet.
 */
export function accentGradient(accentHex?: string | null): string {
  const theme = getFestivalTheme(accentHex);
  return `radial-gradient(120% 120% at 20% 0%, ${theme.accentLight} 0%, ${theme.accent} 35%, ${theme.accentDark} 70%, #0A0A0A 100%)`;
}

/** Pick readable foreground (black/white) for a given background hex. */
export function readableOn(hex: string): string {
  const { r, g, b } = hexToRgb(hex);
  // perceived luminance
  const luma = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luma > 0.6 ? "#0A0A0A" : "#FFFFFF";
}
