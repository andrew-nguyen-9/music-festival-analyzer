import type { CSSProperties, ReactNode } from "react";
import { getFestivalTheme, themeToCssVars } from "@/lib/festival-theme";

interface Props {
  accentColor?: string | null;
  children: ReactNode;
  className?: string;
}

/**
 * Wraps a subtree and injects the festival palette as CSS variables, so
 * `text-accent`, `bg-accent`, etc. resolve to this festival's colors.
 * Server-safe (pure inline style).
 */
export default function FestivalThemeStyle({
  accentColor,
  children,
  className,
}: Props) {
  const theme = getFestivalTheme(accentColor);
  const style = themeToCssVars(theme) as CSSProperties;
  // `festival-theme` is the hook the color-blind a11y palettes use to override
  // this per-festival accent (see globals.css → html.cb-*).
  return (
    <div style={style} className={["festival-theme", className].filter(Boolean).join(" ")}>
      {children}
    </div>
  );
}
