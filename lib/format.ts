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

export type FestivalState = "passed" | "schedule" | "lineup" | "tbd";

/**
 * Derives the festival page display state purely from data:
 *   passed   — end_date is in the past
 *   schedule — lineup rows exist and at least one has a `day` set
 *   lineup   — lineup rows exist but no day-level schedule
 *   tbd      — no lineup rows at all
 */
export function getFestivalState(
  endDate: string | null,
  lineupCount: number,
  hasSchedule: boolean,
): FestivalState {
  const today = new Date().toISOString().slice(0, 10);
  if (endDate && endDate < today) return "passed";
  if (lineupCount === 0) return "tbd";
  if (hasSchedule) return "schedule";
  return "lineup";
}

/**
 * Given lineup entries, returns true if at least one has two distinct
 * weekends worth of dates (i.e. dates span more than 7 days apart).
 */
export function hasMultipleWeekends(days: (string | null)[]): boolean {
  const dates = days
    .filter((d): d is string => d != null)
    .map((d) => new Date(d + "T00:00:00").getTime())
    .sort((a, b) => a - b);
  if (dates.length < 2) return false;
  const spanDays = (dates[dates.length - 1] - dates[0]) / 86_400_000;
  return spanDays > 7;
}

// ── Set-time helpers (shared by ScheduleBoard + the v2.8 wallpaper) ────

/** Minutes since midnight for a "HH:MM[:SS]" set time. Pre-dawn hours (0–6)
 *  wrap past 24 so a 1am set sorts after an 11pm set on the same festival night. */
export function timeToMinutes(t: string): number {
  const [h, m] = t.split(":").map(Number);
  return (h < 7 ? h + 24 : h) * 60 + (m ?? 0);
}

/** "21:30:00" → "9:30pm" (times are local to the festival timezone). */
export function fmtSetTime(t: string): string {
  const [h, m] = t.split(":").map(Number);
  const hour = h % 12 || 12;
  const ampm = h < 12 || h === 24 ? "am" : "pm";
  return m === 0
    ? `${hour}${ampm}`
    : `${hour}:${String(m).padStart(2, "0")}${ampm}`;
}

/** ISO date → "Fri, Aug 1". */
export function fmtDayLabel(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

/** Groups a flat lineup by ISO date string. */
export function groupLineupByDay<T extends { day: string | null }>(
  lineup: T[],
): Map<string, T[]> {
  const map = new Map<string, T[]>();
  for (const entry of lineup) {
    const key = entry.day ?? "TBD";
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(entry);
  }
  return map;
}
