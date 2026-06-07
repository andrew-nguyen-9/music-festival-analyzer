// ─────────────────────────────────────────────────────────────
// Small formatting helpers. No external deps.
// ─────────────────────────────────────────────────────────────

/** Format a festival's date range, e.g. "Jul 30 – Aug 2, 2026". */
export function formatDateRange(
  start?: string | null,
  end?: string | null,
): string {
  if (!start) return "Dates TBA";
  const s = new Date(start + "T00:00:00");
  const e = end ? new Date(end + "T00:00:00") : null;
  const month = (d: Date) => d.toLocaleDateString("en-US", { month: "short" });
  const day = (d: Date) => d.getDate();
  const year = (d: Date) => d.getFullYear();

  if (!e || s.getTime() === e.getTime()) {
    return `${month(s)} ${day(s)}, ${year(s)}`;
  }
  if (s.getFullYear() === e.getFullYear() && s.getMonth() === e.getMonth()) {
    return `${month(s)} ${day(s)}–${day(e)}, ${year(e)}`;
  }
  if (s.getFullYear() === e.getFullYear()) {
    return `${month(s)} ${day(s)} – ${month(e)} ${day(e)}, ${year(e)}`;
  }
  return `${month(s)} ${day(s)}, ${year(s)} – ${month(e)} ${day(e)}, ${year(e)}`;
}

/** "Chicago, IL" — gracefully drops missing parts. */
export function formatLocation(
  city?: string | null,
  state?: string | null,
): string {
  return [city, state].filter(Boolean).join(", ") || "Location TBA";
}

/** Compact follower counts: 1234567 -> "1.2M". */
export function formatCount(n?: number | null): string {
  if (n == null) return "—";
  if (n < 1000) return String(n);
  if (n < 1_000_000) return (n / 1000).toFixed(n < 10_000 ? 1 : 0) + "K";
  return (n / 1_000_000).toFixed(n < 10_000_000 ? 1 : 0) + "M";
}

/** Relative-ish time for social posts. */
export function timeAgo(iso?: string | null): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  const diff = Date.now() - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

/** The year to query lineups for. Defaults to the festival's start year. */
export function festivalYear(startDate?: string | null): number {
  if (startDate) {
    const y = new Date(startDate + "T00:00:00").getFullYear();
    if (!Number.isNaN(y)) return y;
  }
  return new Date().getFullYear();
}
