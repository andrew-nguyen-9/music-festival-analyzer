"use client";

/**
 * Footer shortcut that opens the accessibility panel (v4.4 SettingsPanel listens
 * for this event). Keeps the footer otherwise server-rendered.
 */
export default function A11yShortcutButton({
  className,
}: {
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={() => window.dispatchEvent(new Event("soundcheck:open-a11y"))}
      className={className}
    >
      Accessibility
    </button>
  );
}
