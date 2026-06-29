"use client";

import { useEffect, useRef, useState } from "react";
import {
  readA11ySettings,
  writeA11ySetting,
  COLORBLIND_OPTIONS,
  FONT_OPTIONS,
  fontLabel,
  type A11ySettings,
  type ColorBlind,
  type FontSize,
} from "@/lib/settings";

/**
 * Accessibility settings panel (v4.4). A gear in the header opens a popover with
 * high-contrast, reduced-motion, color-blind palette, and font-size controls.
 * Everything persists to localStorage and applies via <html> classes (see
 * lib/settings.ts + globals.css). Opened from the footer too via the
 * `soundcheck:open-a11y` event (#5).
 */
export default function SettingsPanel() {
  const [open, setOpen] = useState(false);
  const [s, setS] = useState<A11ySettings | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => setS(readA11ySettings()), []);

  // Allow the footer shortcut (and anything else) to open the panel.
  useEffect(() => {
    const openIt = () => setOpen(true);
    window.addEventListener("soundcheck:open-a11y", openIt);
    return () => window.removeEventListener("soundcheck:open-a11y", openIt);
  }, []);

  // Close on outside-click / Escape.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function set<K extends keyof A11ySettings>(key: K, value: A11ySettings[K]) {
    setS(writeA11ySetting(key, value));
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label="Accessibility settings"
        aria-expanded={open}
        title="Accessibility"
        className="grid h-8 w-8 place-items-center rounded-full border border-[color:var(--border)] text-[color:var(--text-muted)] transition-colors hover:text-[color:var(--text)]"
      >
        <GearIcon />
      </button>

      {open && s && (
        <div
          role="dialog"
          aria-label="Accessibility settings"
          className="absolute right-0 top-10 z-50 w-72 rounded-2xl border border-[color:var(--border)] bg-surface-elevated p-4 shadow-2xl"
        >
          <p className="mb-3 text-label uppercase tracking-[0.12em] text-[color:var(--text-muted)]">
            Accessibility
          </p>

          <Row label="High contrast">
            <Switch
              on={s.contrast}
              onToggle={() => set("contrast", !s.contrast)}
              label="High contrast"
            />
          </Row>

          <Row label="Reduce motion">
            <Switch
              on={s.motion}
              onToggle={() => set("motion", !s.motion)}
              label="Reduce motion"
            />
          </Row>

          <Row label="Color vision">
            <select
              value={s.colorblind}
              onChange={(e) => set("colorblind", e.target.value as ColorBlind)}
              aria-label="Color vision palette"
              className="rounded-lg border border-[color:var(--border)] bg-surface px-2 py-1 text-label capitalize text-[color:var(--text)]"
            >
              {COLORBLIND_OPTIONS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </Row>

          <Row label="Text size">
            <div className="flex gap-1" role="group" aria-label="Text size">
              {FONT_OPTIONS.map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => set("font", f as FontSize)}
                  aria-pressed={s.font === f}
                  className={`h-7 w-8 rounded-md border text-label transition-colors ${
                    s.font === f
                      ? "border-accent bg-accent text-black"
                      : "border-[color:var(--border)] text-[color:var(--text-muted)] hover:text-[color:var(--text)]"
                  }`}
                >
                  {fontLabel(f)}
                </button>
              ))}
            </div>
          </Row>
        </div>
      )}
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-2 text-body text-[color:var(--text)]">
      <span>{label}</span>
      {children}
    </div>
  );
}

function Switch({
  on,
  onToggle,
  label,
}: {
  on: boolean;
  onToggle: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={onToggle}
      className={`relative h-6 w-11 rounded-full transition-colors ${
        on ? "bg-accent" : "bg-[color:var(--border)]"
      }`}
    >
      <span
        className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
          on ? "translate-x-[1.375rem]" : "translate-x-0.5"
        }`}
      />
    </button>
  );
}

function GearIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}
