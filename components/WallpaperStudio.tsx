"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { getFestivalTheme } from "@/lib/festival-theme";
import { timeToMinutes, fmtSetTime, fmtDayLabel } from "@/lib/format";
import type { Festival, LineupEntry, Stage } from "@/lib/types";

interface Props {
  festival: Festival;
  lineup: LineupEntry[];
  stages: Stage[];
}

// Phone canvas (iPhone Pro logical ×3). Rendered at full res, previewed scaled.
const W = 1170;
const H = 2532;

/**
 * Client-canvas phone-wallpaper generator (v2.8). Pick a day, toggle the sets you
 * want, download a PNG of your schedule with set times + stage locations in the
 * festival's accent. Pure vector/text on canvas — no remote images, so it taints
 * nothing and works offline (the default decision over a server render).
 */
export default function WallpaperStudio({ festival, lineup, stages }: Props) {
  const theme = getFestivalTheme(festival.accent_color);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Days that actually have scheduled set times.
  const days = useMemo(() => {
    const set = new Set<string>();
    for (const e of lineup) if (e.day && e.set_time_start) set.add(e.day);
    return [...set].sort();
  }, [lineup]);

  const [day, setDay] = useState<string>(days[0] ?? "");
  const [chosen, setChosen] = useState<Set<string>>(new Set());

  // Sets for the active day, sorted by (wrapped) start time.
  const daySets = useMemo(
    () =>
      lineup
        .filter((e) => e.day === day && e.set_time_start)
        .sort(
          (a, b) =>
            timeToMinutes(a.set_time_start!) - timeToMinutes(b.set_time_start!),
        ),
    [lineup, day],
  );

  // Default: everything on the day selected.
  useEffect(() => {
    setChosen(new Set(daySets.map((e) => e.id)));
  }, [daySets]);

  const stageCoords = useMemo(() => {
    const m = new Map<string, Stage>();
    for (const s of stages) if (s.name) m.set(s.name, s);
    return m;
  }, [stages]);

  // Redraw whenever the selection changes.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const picked = daySets.filter((e) => chosen.has(e.id));
    // Wait for the display font so canvas text matches the app.
    const draw = () => paint(ctx, { festival, theme, day, picked, stageCoords });
    if (document.fonts?.ready) document.fonts.ready.then(draw).catch(draw);
    else draw();
  }, [festival, theme, day, daySets, chosen, stageCoords]);

  function toggle(id: string) {
    setChosen((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function download() {
    const canvas = canvasRef.current;
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
        <p className="mt-3 text-body text-white/60">
          {festival.name} doesn’t have set times yet, so there’s nothing to turn
          into a wallpaper. Check back once the schedule is published.
        </p>
      </section>
    );
  }

  return (
    <section className="mx-auto grid max-w-wide gap-10 px-5 py-16 md:grid-cols-[1fr,minmax(280px,360px)] md:px-8">
      {/* Controls */}
      <div>
        <h1 className="text-display-lg text-white">Make your wallpaper</h1>
        <p className="mt-2 text-body text-white/60">
          Pick a day and the sets you want. We’ll render a phone wallpaper with
          times and stages in {festival.name}’s colors.
        </p>

        <div className="mt-6 flex flex-wrap gap-2">
          {days.map((d) => (
            <button
              key={d}
              onClick={() => setDay(d)}
              className={
                "rounded-full px-4 py-2 text-label font-semibold uppercase tracking-wide transition-colors " +
                (d === day
                  ? "bg-accent text-black"
                  : "border border-white/20 text-white/70 hover:text-white")
              }
            >
              {fmtDayLabel(d)}
            </button>
          ))}
        </div>

        <ul className="mt-6 divide-y divide-white/10 rounded-2xl border border-white/10">
          {daySets.map((e) => (
            <li key={e.id}>
              <label className="flex cursor-pointer items-center gap-3 px-4 py-3">
                <input
                  type="checkbox"
                  checked={chosen.has(e.id)}
                  onChange={() => toggle(e.id)}
                  className="h-4 w-4 accent-[var(--accent)]"
                />
                <span className="w-20 shrink-0 text-label font-semibold text-accent">
                  {fmtSetTime(e.set_time_start!)}
                </span>
                <span className="flex-1 text-body text-white">{e.artist.name}</span>
                <span className="truncate text-label text-white/50">
                  {e.stage ?? ""}
                </span>
              </label>
            </li>
          ))}
        </ul>

        <button
          onClick={download}
          className="mt-6 rounded-full bg-accent px-6 py-3 text-label font-semibold uppercase tracking-wide text-black transition-transform hover:scale-[1.02]"
        >
          Download wallpaper
        </button>
      </div>

      {/* Live preview */}
      <div className="justify-self-center">
        <canvas
          ref={canvasRef}
          width={W}
          height={H}
          className="h-auto w-full max-w-[300px] rounded-[2rem] border border-white/15 shadow-2xl"
        />
      </div>
    </section>
  );
}

// ── Canvas painting (pure given its args) ──────────────────────
interface PaintArgs {
  festival: Festival;
  theme: ReturnType<typeof getFestivalTheme>;
  day: string;
  picked: LineupEntry[];
  stageCoords: Map<string, Stage>;
}

function paint(ctx: CanvasRenderingContext2D, a: PaintArgs) {
  const { festival, theme, day, picked, stageCoords } = a;

  // Background + accent glow.
  ctx.fillStyle = "#0A0A0A";
  ctx.fillRect(0, 0, W, H);
  const glow = ctx.createRadialGradient(W * 0.2, 120, 40, W * 0.2, 120, W);
  glow.addColorStop(0, hexA(theme.accent, 0.28));
  glow.addColorStop(1, "rgba(10,10,10,0)");
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, W, H);

  const pad = 96;
  let y = 300;

  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = theme.accent;
  ctx.font = "600 40px 'Space Grotesk', system-ui, sans-serif";
  ctx.fillText("MY DAY AT", pad, y);
  y += 90;

  ctx.fillStyle = "#FFFFFF";
  ctx.font = "700 96px 'Space Grotesk', system-ui, sans-serif";
  const nameLines = wrap(ctx, festival.name.toUpperCase(), W - pad * 2);
  nameLines.forEach((line, i) => ctx.fillText(line, pad, y + i * 100));
  y += 100 * nameLines.length + 20;

  ctx.fillStyle = theme.accentLight;
  ctx.font = "500 44px 'Space Grotesk', system-ui, sans-serif";
  ctx.fillText(day ? fmtDayLabel(day) : "", pad, y);
  y += 70;

  // Divider.
  ctx.strokeStyle = "rgba(255,255,255,0.15)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(pad, y);
  ctx.lineTo(W - pad, y);
  ctx.stroke();
  y += 70;

  // Set list — scale line height so a full day still fits above the footer.
  const footerTop = H - 220;
  const rows = picked.length || 1;
  const lh = Math.min(96, Math.max(54, (footerTop - y) / rows));

  ctx.textBaseline = "middle";
  for (const e of picked) {
    if (y > footerTop - lh) break;
    ctx.fillStyle = theme.accent;
    ctx.font = `600 ${Math.round(lh * 0.32)}px 'Space Grotesk', system-ui, sans-serif`;
    ctx.fillText(fmtSetTime(e.set_time_start!), pad, y + lh / 2);

    ctx.fillStyle = "#FFFFFF";
    ctx.font = `600 ${Math.round(lh * 0.4)}px Inter, system-ui, sans-serif`;
    ctx.fillText(truncate(ctx, e.artist.name, W - pad * 2 - 230), pad + 230, y + lh / 2 - lh * 0.16);

    const stage = e.stage ?? "";
    if (stage) {
      ctx.fillStyle = "rgba(255,255,255,0.5)";
      ctx.font = `400 ${Math.round(lh * 0.26)}px Inter, system-ui, sans-serif`;
      // Mark stages that have geocoded coordinates (v2.8.4).
      const located = stageCoords.get(stage)?.latitude != null;
      ctx.fillText(`${located ? "● " : ""}${stage}`, pad + 230, y + lh / 2 + lh * 0.24);
    }
    y += lh;
  }

  // Footer brand.
  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = "rgba(255,255,255,0.4)";
  ctx.font = "500 34px 'Space Grotesk', system-ui, sans-serif";
  ctx.fillText("festivalanalyzer", pad, H - 120);
}

// ── tiny canvas text helpers ──
function wrap(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxW: number,
): string[] {
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
  return lines.slice(0, 3);
}

function truncate(ctx: CanvasRenderingContext2D, text: string, maxW: number): string {
  if (ctx.measureText(text).width <= maxW) return text;
  let t = text;
  while (t.length > 1 && ctx.measureText(t + "…").width > maxW) t = t.slice(0, -1);
  return t + "…";
}

function hexA(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}
