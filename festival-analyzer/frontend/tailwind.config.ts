import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Festival theme is injected at runtime via CSS variables
        // (see lib/festival-theme.ts + <FestivalThemeStyle/>).
        accent: "var(--accent)",
        "accent-light": "var(--accent-light)",
        "accent-dark": "var(--accent-dark)",
        surface: "var(--surface)",
        "surface-elevated": "var(--surface-elevated)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "system-ui", "sans-serif"],
      },
      fontSize: {
        // UI_SPEC typography scale
        "display-xl": ["clamp(3.5rem, 10vw, 7.5rem)", { lineHeight: "0.95", letterSpacing: "-0.03em", fontWeight: "800" }],
        "display-lg": ["clamp(2.5rem, 6vw, 5rem)", { lineHeight: "1.0", letterSpacing: "-0.02em", fontWeight: "700" }],
        "display-md": ["clamp(1.75rem, 3.5vw, 3rem)", { lineHeight: "1.05", letterSpacing: "-0.01em", fontWeight: "600" }],
        heading: ["clamp(1.25rem, 2.2vw, 2rem)", { lineHeight: "1.15", fontWeight: "600" }],
        "body-lg": ["1.125rem", { lineHeight: "1.6" }],
        body: ["1rem", { lineHeight: "1.6" }],
        label: ["0.8125rem", { lineHeight: "1.2", letterSpacing: "0.02em", fontWeight: "500" }],
      },
      maxWidth: {
        wide: "1440px",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.5s ease-out both",
      },
    },
  },
  plugins: [],
};

export default config;
