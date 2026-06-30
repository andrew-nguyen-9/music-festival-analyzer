"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { getFestivalTheme } from "@/lib/festival-theme";
import { timeToMinutes, fmtSetTime, fmtDayLabel } from "@/lib/format";
import type { Festival, LineupEntry } from "@/lib/types";

interface Props {
  festival: Festival;
  lineup: LineupEntry[];
}

// Phone canvas (iPhone Pro logical ×3). Rendered at full res, previewed scaled.
const W = 1170;
const H = 2532;
const MAX_SETS = 10; // artists shown on the wallpaper

interface SetRow {
  id: string;
  name: string;
  start: string;
  stage: string | null;
  headliner: boolean;
  popularity: number;
}

interface Palette {
  name: string;
  bg: string;
  fg: string;
  /** null = use the festival accent. */
  accent: string | null;
}

/**
 * Make-your-wallpaper studio (v4.9 rebuild, v4.10 by-day). A lock-screen wallpaper
 * of YOUR festival day — pick a day, choose up to 10 sets, rendered latest →
 * earliest with set times + stages. Strict 3-zone geometry (clock space on top,
 * centered schedule, OS-UI safe zone on the bottom), color customization, and
 * Soundcheck branding. Pure canvas — no remote images, exports a real-res PNG.
 */
export default function WallpaperStudio({ festival, lineup }: Props) {
  const theme = getFestivalTheme(festival.accent_color);
  // Two previews (desktop side-panel + mobile stacked) each need their own canvas
  // — one shared ref would only attach to the last-mounted (hidden) one.
  const desktopCanvasRef = useRef<HTMLCanvasElement>(null);
  const mobileCanvasRef = useRef<HTMLCanvasElement>(null);

  // Days that actually have scheduled set times.
  const days = useMemo(() => {
    const s = new Set<string>();
    for (const e of lineup) if (e.day && e.set_time_start) s.add(e.day);
    return [...s].sort();
  }, [lineup]);

  const [day, setDay] = useState<string>(days[0] ?? "");
  const [stageFilter, setStageFilter] = useState("all");
  const [chosen, setChosen] = useState<Set<string>>(new Set()); // starts EMPTY
  const [sheetOpen, setSheetOpen] = useState(false);

  // Reset the selection when the day changes — set ids differ per day.
  useEffect(() => setChosen(new Set()), [day]);

  // All sets for the active day, latest → earliest (timeToMinutes wraps past midnight).
  const allDaySets = useMemo<SetRow[]>(
    () =>
      lineup
        .filter((e) => e.day === day && e.set_time_start)
        .map((e) => ({
          id: e.id,
          name: e.artist.name,
          start: e.set_time_start!,
          stage: e.stage,
          headliner: !!e.is_headliner,
          popularity: e.artist.spotify_popularity ?? 0,
        }))
        .sort((a, b) => timeToMinutes(b.start) - timeToMinutes(a.start)),
    [lineup, day],
  );

  const stagesForDay = useMemo(() => {
    const s = new Set<string>();
    for (const e of allDaySets) if (e.stage) s.add(e.stage);
    return [...s].sort();
  }, [allDaySets]);

  const filtered = useMemo(
    () => allDaySets.filter((e) => stageFilter === "all" || e.stage === stageFilter),
    [allDaySets, stageFilter],
  );

  // Chosen sets, latest → earliest, capped at MAX_SETS.
  const chosenSets = useMemo(
    () => allDaySets.filter((e) => chosen.has(e.id)).slice(0, MAX_SETS),
    [allDaySets, chosen],
  );

  // ── Colors ────────────────────────────────────────────────────
  const palettes: Palette[] = useMemo(
    () => [
      { name: "Dark", bg: "#0A0A0A", fg: "#FFFFFF", accent: null },
      { name: "Light", bg: "#F6F6F7", fg: "#0D0D0F", accent: null },
      { name: "Accent", bg: theme.accentDark, fg: "#FFFFFF", accent: theme.accentLight },
      { name: "Mono", bg: "#000000", fg: "#FFFFFF", accent: "#FFFFFF" },
    ],
    [theme],
  );
  const [bg, setBg] = useState(palettes[0].bg);
  const [fg, setFg] = useState(palettes[0].fg);
  const [accent, setAccent] = useState<string>(theme.accent);

  function applyPalette(p: Palette) {
    setBg(p.bg);
    setFg(p.fg);
    setAccent(p.accent ?? theme.accent);
  }

  // ── Draw (to both canvases; only one is visible per breakpoint) ──
  useEffect(() => {
    const args: PaintArgs = {
      festival,
      day,
      sets: chosenSets,
      bg,
      fg,
      accent,
    };
    const draw = () => {
      for (const ref of [desktopCanvasRef, mobileCanvasRef]) {
        const ctx = ref.current?.getContext("2d");
        if (ctx) paint(ctx, args);
      }
    };
    if (document.fonts?.ready) document.fonts.ready.then(draw).catch(draw);
    else draw();
  }, [festival, day, chosenSets, bg, fg, accent]);

  // ── Selection helpers ─────────────────────────────────────────
  function toggle(id: string) {
    setChosen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < MAX_SETS) next.add(id);
      return next;
    });
  }
  function addHeadliners() {
    const headliners = allDaySets.filter((e) => e.headliner);
    const picks = (headliners.length > 0
      ? headliners
      : [...allDaySets].sort((a, b) => b.popularity - a.popularity)
    ).slice(0, MAX_SETS);
    setChosen(new Set(picks.map((e) => e.id)));
  }
  function clearAll() {
    setChosen(new Set());
  }

  function download() {
    const canvas = desktopCanvasRef.current ?? mobileCanvasRef.current;
    if (!canvas) return;
    canvas.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${festival.slug}-${day || "schedule"}-wallpaper.png`;
      a.click();
      URL.revokeObjectURL(url);
    }, "image/png");
  }

  if (days.length === 0) {
    return (
      <section className="mx-auto max-w-wide px-5 py-20 text-center md:px-8">
        <h1 className="text-display-md text-white">No schedule yet</h1>
        <p className="mt-3 text-body text-[color:var(--text-muted)]">
          {festival.name} doesn&apos;t have set times yet, so there&apos;s nothing
          to turn into a day wallpaper. Check back once the schedule is published.
        </p>
      </section>
    );
  }

  const controls = (
    <Controls
      festival={festival}
      days={days}
      day={day}
      setDay={setDay}
      filtered={filtered}
      chosen={chosen}
      chosenCount={chosenSets.length}
      toggle={toggle}
      addHeadliners={addHeadliners}
      clearAll={clearAll}
      stagesForDay={stagesForDay}
      stageFilter={stageFilter}
      setStageFilter={setStageFilter}
      palettes={palettes}
      applyPalette={applyPalette}
      bg={bg}
      setBg={setBg}
      fg={fg}
      setFg={setFg}
      download={download}
    />
  );

  return (
    <section className="mx-auto max-w-wide px-5 pb-10 pt-28 md:px-8 md:pt-32">
      {/* pt-28/32 clears the fixed, transparent site Nav (matches other pages). */}
      {/* Desktop: controls left, phone preview pinned right. */}
      <div className="hidden gap-10 md:grid md:grid-cols-[1fr,minmax(300px,340px)]">
        <div className="max-h-[82vh] overflow-y-auto pr-2">{controls}</div>
        <div className="sticky top-24 self-start justify-self-center">
          <PhonePreview canvasRef={desktopCanvasRef} />
        </div>
      </div>

      {/* Mobile: wallpaper fills the screen; a pull-up sheet holds the controls. */}
      <div className="md:hidden">
        <div className="flex flex-col items-center">
          <PhonePreview canvasRef={mobileCanvasRef} />
          <button
            onClick={() => setSheetOpen(true)}
            className="mt-6 w-full rounded-full bg-accent px-6 py-3.5 text-label font-semibold uppercase tracking-wide text-black"
          >
            Customize ({chosenSets.length})
          </button>
        </div>
        {sheetOpen && (
          <div className="fixed inset-0 z-50 flex flex-col justify-end">
            <button
              aria-label="Close"
              onClick={() => setSheetOpen(false)}
              className="absolute inset-0 bg-black/60"
            />
            <div className="relative max-h-[85vh] overflow-y-auto rounded-t-3xl border-t border-[color:var(--border)] bg-surface p-5">
              <div className="mx-auto mb-4 h-1.5 w-12 rounded-full bg-white/25" />
              {controls}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function PhonePreview({
  canvasRef,
}: {
  canvasRef: React.RefObject<HTMLCanvasElement>;
}) {
  return (
    <div className="rounded-[2.5rem] border-[6px] border-black/80 bg-black shadow-2xl ring-1 ring-white/10">
      <canvas
        ref={canvasRef}
        width={W}
        height={H}
        className="block h-auto w-full max-w-[300px] rounded-[2rem]"
      />
    </div>
  );
}

// ── Controls panel (shared desktop + mobile) ──────────────────────
interface ControlsProps {
  festival: Festival;
  days: string[];
  day: string;
  setDay: (d: string) => void;
  filtered: SetRow[];
  chosen: Set<string>;
  chosenCount: number;
  toggle: (id: string) => void;
  addHeadliners: () => void;
  clearAll: () => void;
  stagesForDay: string[];
  stageFilter: string;
  setStageFilter: (s: string) => void;
  palettes: Palette[];
  applyPalette: (p: Palette) => void;
  bg: string;
  setBg: (s: string) => void;
  fg: string;
  setFg: (s: string) => void;
  download: () => void;
}

function Controls(p: ControlsProps) {
  const atMax = p.chosenCount >= MAX_SETS;
  return (
    <div>
      <h1 className="text-display-md text-white">Make your day wallpaper</h1>
      <p className="mt-1 text-body text-[color:var(--text-muted)]">
        Pick a day and up to {MAX_SETS} sets — {p.festival.name}.
      </p>

      {/* Day tabs */}
      {p.days.length > 1 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {p.days.map((d) => (
            <button
              key={d}
              onClick={() => p.setDay(d)}
              className={
                "rounded-full px-4 py-2 text-label font-semibold uppercase tracking-wide transition-colors " +
                (d === p.day
                  ? "bg-accent text-black"
                  : "border border-[color:var(--border)] text-[color:var(--text-muted)] hover:text-[color:var(--text)]")
              }
            >
              {fmtDayLabel(d)}
            </button>
          ))}
        </div>
      )}

      {/* Shortcuts */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          onClick={p.addHeadliners}
          className="rounded-full bg-accent px-4 py-2 text-label font-semibold uppercase tracking-wide text-black"
        >
          + Add headliners
        </button>
        <button
          onClick={p.clearAll}
          className="rounded-full border border-[color:var(--border)] px-4 py-2 text-label font-semibold uppercase tracking-wide text-[color:var(--text-muted)] hover:text-[color:var(--text)]"
        >
          Clear
        </button>
        {p.stagesForDay.length > 0 && (
          <Select label="Stage" value={p.stageFilter} onChange={p.setStageFilter}
            options={["all", ...p.stagesForDay]} />
        )}
        <span className="ml-auto self-center text-label text-[color:var(--text-muted)]">
          {p.chosenCount}/{MAX_SETS}
        </span>
      </div>

      {/* Colors */}
      <div className="mt-5">
        <p className="mb-2 text-label uppercase tracking-widest text-[color:var(--text-muted)]">Colors</p>
        <div className="flex flex-wrap items-center gap-2">
          {p.palettes.map((pal) => (
            <button
              key={pal.name}
              onClick={() => p.applyPalette(pal)}
              className="flex items-center gap-1.5 rounded-full border border-[color:var(--border)] px-3 py-1.5 text-label text-[color:var(--text)]"
            >
              <span className="h-3 w-3 rounded-full" style={{ backgroundColor: pal.bg, boxShadow: `inset 0 0 0 2px ${pal.fg}` }} />
              {pal.name}
            </button>
          ))}
          <label className="flex items-center gap-1.5 text-label text-[color:var(--text-muted)]">
            BG
            <input type="color" value={p.bg} onChange={(e) => p.setBg(e.target.value)}
              className="h-7 w-7 cursor-pointer rounded border border-[color:var(--border)] bg-transparent" />
          </label>
          <label className="flex items-center gap-1.5 text-label text-[color:var(--text-muted)]">
            Text
            <input type="color" value={p.fg} onChange={(e) => p.setFg(e.target.value)}
              className="h-7 w-7 cursor-pointer rounded border border-[color:var(--border)] bg-transparent" />
          </label>
        </div>
      </div>

      {/* Set checklist (latest → earliest) */}
      <ul className="mt-5 max-h-[40vh] divide-y divide-white/10 overflow-y-auto rounded-2xl border border-[color:var(--border)]">
        {p.filtered.map((e) => {
          const on = p.chosen.has(e.id);
          return (
            <li key={e.id}>
              <label
                className={`flex cursor-pointer items-center gap-3 px-4 py-2.5 ${
                  !on && atMax ? "opacity-40" : ""
                }`}
              >
                <input
                  type="checkbox"
                  checked={on}
                  disabled={!on && atMax}
                  onChange={() => p.toggle(e.id)}
                  className="h-4 w-4 accent-[var(--accent)]"
                />
                <span className="w-20 shrink-0 text-label font-semibold text-accent">
                  {fmtSetTime(e.start)}
                </span>
                <span className="flex-1 truncate text-body text-[color:var(--text)]">{e.name}</span>
                {e.headliner && <span className="text-[10px] font-bold uppercase text-accent">★</span>}
                {e.stage && (
                  <span className="max-w-[35%] truncate text-label text-[color:var(--text-muted)]">{e.stage}</span>
                )}
              </label>
            </li>
          );
        })}
      </ul>

      <button
        onClick={p.download}
        disabled={p.chosenCount === 0}
        className="mt-5 w-full rounded-full bg-accent px-6 py-3.5 text-label font-semibold uppercase tracking-wide text-black transition-transform hover:scale-[1.01] disabled:cursor-not-allowed disabled:opacity-40"
      >
        Download wallpaper
      </button>
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <label className="flex items-center gap-2 text-label text-[color:var(--text-muted)]">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-[color:var(--border)] bg-surface-elevated px-2 py-1.5 capitalize text-[color:var(--text)]"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}

// ── Canvas painting — strict 3-zone lock-screen geometry ──────────
interface PaintArgs {
  festival: Festival;
  day: string;
  sets: SetRow[];
  bg: string;
  fg: string;
  accent: string;
}

function paint(ctx: CanvasRenderingContext2D, a: PaintArgs) {
  const { festival, day, sets, bg, fg, accent } = a;

  // Background + a soft accent glow up top (sits behind the clock zone).
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);
  const glow = ctx.createRadialGradient(W / 2, H * 0.16, 60, W / 2, H * 0.16, W * 0.9);
  glow.addColorStop(0, hexA(accent, 0.22));
  glow.addColorStop(1, hexA(accent, 0));
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, W, H);

  ctx.textAlign = "center";

  // ── Zone boundaries ──
  const BOTTOM_ZONE = (H * 2) / 3; // OS UI overlays below this — kept clear

  // Header sits at the top of the center zone, just clear of the clock zone.
  let y = H / 3 + 70;
  ctx.fillStyle = accent;
  ctx.font = "600 38px 'Space Grotesk', system-ui, sans-serif";
  ctx.fillText("MY DAY AT", W / 2, y);
  y += 96;
  ctx.fillStyle = fg;
  ctx.font = "700 66px 'Space Grotesk', system-ui, sans-serif";
  for (const line of wrap(ctx, festival.name.toUpperCase(), W * 0.84).slice(0, 2)) {
    ctx.fillText(line, W / 2, y);
    y += 74;
  }
  if (day) {
    y += 18;
    ctx.fillStyle = hexA(accent, 0.9);
    ctx.font = "500 42px 'Space Grotesk', system-ui, sans-serif";
    ctx.fillText(fmtDayLabel(day).toUpperCase(), W / 2, y);
    y += 30;
  }

  // Divider under the header.
  y += 44;
  ctx.strokeStyle = hexA(fg, 0.18);
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(W * 0.22, y);
  ctx.lineTo(W * 0.78, y);
  ctx.stroke();

  // ── Schedule list: time + artist + stage, latest → earliest, auto-scaled ──
  const listTop = y + 60;
  const listBottom = BOTTOM_ZONE + H * 0.13; // into the upper bottom-zone, clear of the home bar
  const n = sets.length;
  if (n > 0) {
    const band = listBottom - listTop;
    const lh = Math.min(150, band / n);
    let nameSize = Math.round(lh * 0.36);
    const subSize = Math.round(lh * 0.2);
    // Shrink the name to the widest entry so nothing clips.
    const fit = () => {
      ctx.font = `600 ${nameSize}px Inter, system-ui, sans-serif`;
      return sets.every((s) => ctx.measureText(s.name).width <= W * 0.84);
    };
    while (nameSize > 18 && !fit()) nameSize -= 2;

    const blockH = lh * n;
    let ly = listTop + (band - blockH) / 2 + lh / 2;
    ctx.textBaseline = "middle";
    for (const s of sets) {
      ctx.fillStyle = fg;
      ctx.font = `600 ${nameSize}px Inter, system-ui, sans-serif`;
      ctx.fillText(truncate(ctx, s.name, W * 0.86), W / 2, ly - subSize * 0.7);

      ctx.font = `500 ${subSize}px Inter, system-ui, sans-serif`;
      const sub = [fmtSetTime(s.start), s.stage].filter(Boolean).join("  ·  ");
      ctx.fillStyle = hexA(accent, 0.95);
      ctx.fillText(sub, W / 2, ly + nameSize * 0.55);
      ly += lh;
    }
  } else {
    ctx.fillStyle = hexA(fg, 0.5);
    ctx.font = "500 40px Inter, system-ui, sans-serif";
    ctx.textBaseline = "middle";
    ctx.fillText("Pick sets to build your day", W / 2, (listTop + listBottom) / 2);
  }

  // ── Branding: Soundcheck wordmark, bottom-center in the safe zone ──
  ctx.textBaseline = "alphabetic";
  const brandY = H * 0.9;
  const grad = ctx.createLinearGradient(W / 2 - 150, 0, W / 2 + 150, 0);
  grad.addColorStop(0, "#FF7A1A");
  grad.addColorStop(1, "#FFC83D");
  ctx.font = "700 40px 'Space Grotesk', system-ui, sans-serif";
  ctx.fillStyle = grad;
  ctx.fillText("◗ SOUNDCHECK", W / 2, brandY);
  ctx.fillStyle = hexA(fg, 0.4);
  ctx.font = "500 26px Inter, system-ui, sans-serif";
  ctx.fillText("soundcheck.an9.dev", W / 2, brandY + 40);
}

// ── tiny canvas text helpers ──
function wrap(ctx: CanvasRenderingContext2D, text: string, maxW: number): string[] {
  const words = text.split(" ");
  const lines: string[] = [];
  let line = "";
  for (const w of words) {
    const test = line ? `${line} ${w}` : w;
    if (ctx.measureText(test).width > maxW && line) {
      lines.push(line);
      line = w;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function truncate(ctx: CanvasRenderingContext2D, text: string, maxW: number): string {
  if (ctx.measureText(text).width <= maxW) return text;
  let t = text;
  while (t.length > 1 && ctx.measureText(t + "…").width > maxW) t = t.slice(0, -1);
  return t + "…";
}

function hexA(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const full = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  const r = parseInt(full.slice(0, 2), 16);
  const g = parseInt(full.slice(2, 4), 16);
  const b = parseInt(full.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}
