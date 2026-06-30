// ─────────────────────────────────────────────────────────────
// Accessibility + theme settings (v4.4). localStorage only — no auth/DB.
// All settings apply via classes / data attrs on <html> + CSS variables in
// globals.css, so they cascade everywhere and survive the light/dark theme.
// The pre-paint inline script in app/layout.tsx mirrors this logic (it can't
// import a module), so keep the class/key names here in sync with that script.
// ─────────────────────────────────────────────────────────────

export type ColorBlind = "none" | "protanopia" | "deuteranopia" | "tritanopia";
export type FontSize = "s" | "m" | "l" | "xl";

export interface A11ySettings {
  contrast: boolean;
  motion: boolean; // true = reduced motion forced on
  colorblind: ColorBlind;
  font: FontSize;
}

export const DEFAULT_A11Y: A11ySettings = {
  contrast: false,
  motion: false,
  colorblind: "none",
  font: "m",
};

export const COLORBLIND_OPTIONS: ColorBlind[] = [
  "none",
  "protanopia",
  "deuteranopia",
  "tritanopia",
];
export const FONT_OPTIONS: FontSize[] = ["s", "m", "l", "xl"];
const FONT_LABEL: Record<FontSize, string> = { s: "S", m: "M", l: "L", xl: "XL" };
export const fontLabel = (f: FontSize) => FONT_LABEL[f];

const KEY: Record<keyof A11ySettings, string> = {
  contrast: "a11y-contrast",
  motion: "a11y-motion",
  colorblind: "a11y-colorblind",
  font: "a11y-font",
};

/** Read settings from localStorage, falling back to defaults (SSR-safe). */
export function readA11ySettings(): A11ySettings {
  if (typeof window === "undefined") return DEFAULT_A11Y;
  try {
    const ls = window.localStorage;
    return {
      contrast: ls.getItem(KEY.contrast) === "on",
      motion: ls.getItem(KEY.motion) === "on",
      colorblind: (ls.getItem(KEY.colorblind) as ColorBlind) || "none",
      font: (ls.getItem(KEY.font) as FontSize) || "m",
    };
  } catch {
    return DEFAULT_A11Y;
  }
}

/** Apply settings to <html> classes (mirrors the pre-paint script). */
export function applyA11ySettings(s: A11ySettings): void {
  const e = document.documentElement;
  e.classList.toggle("hc", s.contrast);
  e.classList.toggle("rm", s.motion);
  for (const c of COLORBLIND_OPTIONS) {
    if (c !== "none") e.classList.toggle(`cb-${c}`, s.colorblind === c);
  }
  for (const f of FONT_OPTIONS) e.classList.toggle(`fs-${f}`, s.font === f);
}

/** Persist a single setting and re-apply. */
export function writeA11ySetting<K extends keyof A11ySettings>(
  key: K,
  value: A11ySettings[K],
): A11ySettings {
  const next = { ...readA11ySettings(), [key]: value };
  try {
    const v =
      typeof value === "boolean" ? (value ? "on" : "off") : String(value);
    window.localStorage.setItem(KEY[key], v);
  } catch {
    /* storage disabled — still applies for this session */
  }
  applyA11ySettings(next);
  // Let JS-driven consumers (e.g. the Framer MotionConfig provider) react live.
  try {
    window.dispatchEvent(
      new CustomEvent("soundcheck:a11y-changed", { detail: next }),
    );
  } catch {
    /* no-op */
  }
  return next;
}
