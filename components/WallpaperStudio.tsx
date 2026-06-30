"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { getFestivalTheme } from "@/lib/festival-theme";
import type { Festival, LineupEntry } from "@/lib/types";

interface Props {
  festival: Festival;
  lineup: LineupEntry[];
}

// Phone canvas (iPhone Pro logical ×3). Rendered at full res, previewed scaled.
const W = 1170;
const H = 2532;
const MAX_ARTISTS = 40;

type Sort = "popularity" | "alpha";

interface PoolArtist {
  id: string;
  name: string;
  popularity: number;
  genres: string[];
  stages: string[];
  headliner: boolean;
}

interface Palette {
  name: string;
  bg: string;
  fg: string;
  /** null = use the festival accent. */
  accent: string | null;
}

/**
 * Make-your-wallpaper studio (v4.9 rebuild). A curated lock-screen wallpaper of
 * the artists YOU pick — starts empty, strict 3-zone geometry (clock space on
 * top, centered artist list, OS-UI safe zone on the bottom), auto-scaling text,
 * stage/genre filters, color customization, and Soundcheck branding. Pure
 * canvas — no remote images, works offline, exports a real-resolution PNG.
 */
export default function WallpaperStudio({ festival, lineup }: Props) {
  const theme = getFestivalTheme(festival.accent_color);
  // Two previews (desktop side-panel + mobile stacked) each need their own canvas
  // — one shared ref would only attach to the last-mounted (hidden) one.
  const desktopCanvasRef = useRef<HTMLCanvasElement>(null);
  const mobileCanvasRef = useRef<HTMLCanvasElement>(null);

  // ── Unique artist pool from the lineup ────────────────────────
  const pool = useMemo<PoolArtist[]>(() => {
    const m = new Map<string, PoolArtist>();
    for (const e of lineup) {
      const a = e.artist;
      if (!a) continue;
      let rec = m.get(a.id);
      if (!rec) {
        rec = {
          id: a.id,
          name: a.name,
          popularity: a.spotify_popularity ?? 0,
          genres: a.genres ?? [],
          stages: [],
          headliner: false,
        };
        m.set(a.id, rec);
      }
      if (e.stage && !rec.stages.includes(e.stage)) rec.stages.push(e.stage);
      if (e.is_headliner) rec.headliner = true;
    }
    return [...m.values()];
  }, [lineup]);

  const hasStages = useMemo(() => pool.some((a) => a.stages.length > 0), [pool]);
  const allGenres = useMemo(() => {
    const s = new Set<string>();
    for (const a of pool) for (const g of a.genres) s.add(g);
    return [...s].sort();
  }, [pool]);
  const allStages = useMemo(() => {
    const s = new Set<string>();
    for (const a of pool) for (const st of a.stages) s.add(st);
    return [...s].sort();
  }, [pool]);

  // ── Filters / sort ────────────────────────────────────────────
  const [stageFilter, setStageFilter] = useState("all");
  const [genreFilter, setGenreFilter] = useState("all");
  const [sort, setSort] = useState<Sort>("popularity");
  const [chosen, setChosen] = useState<Set<string>>(new Set()); // starts EMPTY
  const [sheetOpen, setSheetOpen] = useState(false);

  const sortFn = useMemo(
    () =>
      sort === "popularity"
        ? (a: PoolArtist, b: PoolArtist) => b.popularity - a.popularity || a.name.localeCompare(b.name)
        : (a: PoolArtist, b: PoolArtist) => a.name.localeCompare(b.name),
    [sort],
  );

  const filtered = useMemo(() => {
    return pool
      .filter((a) => stageFilter === "all" || a.stages.includes(stageFilter))
      .filter((a) => genreFilter === "all" || a.genres.includes(genreFilter))
      .sort(sortFn);
  }, [pool, stageFilter, genreFilter, sortFn]);

  // Chosen artists, in the current sort order, capped.
  const chosenArtists = useMemo(
    () => pool.filter((a) => chosen.has(a.id)).sort(sortFn).slice(0, MAX_ARTISTS),
    [pool, chosen, sortFn],
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
      names: chosenArtists.map((a) => a.name),
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
  }, [festival, chosenArtists, bg, fg, accent]);

  // ── Selection helpers ─────────────────────────────────────────
  function toggle(id: string) {
    setChosen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < MAX_ARTISTS) next.add(id);
      return next;
    });
  }
  function addHeadliners() {
    const headliners = pool.filter((a) => a.headliner);
    const picks = (headliners.length > 0
      ? headliners
      : [...pool].sort((a, b) => b.popularity - a.popularity).slice(0, 8)
    ).slice(0, MAX_ARTISTS);
    setChosen(new Set(picks.map((a) => a.id)));
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
      a.download = `${festival.slug}-wallpaper.png`;
      a.click();
      URL.revokeObjectURL(url);
    }, "image/png");
  }

  if (pool.length === 0) {
    return (
      <section className="mx-auto max-w-wide px-5 py-20 text-center md:px-8">
        <h1 className="text-display-md text-white">No lineup yet</h1>
        <p className="mt-3 text-body text-[color:var(--text-muted)]">
          {festival.name} doesn&apos;t have a lineup to turn into a wallpaper yet.
          Check back once it&apos;s announced.
        </p>
      </section>
    );
  }

  const controls = (
    <Controls
      festival={festival}
      filtered={filtered}
      chosen={chosen}
      chosenCount={chosenArtists.length}
      toggle={toggle}
      addHeadliners={addHeadliners}
      clearAll={clearAll}
      hasStages={hasStages}
      allStages={allStages}
      allGenres={allGenres}
      stageFilter={stageFilter}
      setStageFilter={setStageFilter}
      genreFilter={genreFilter}
      setGenreFilter={setGenreFilter}
      sort={sort}
      setSort={setSort}
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
    <section className="mx-auto max-w-wide px-5 py-10 md:px-8">
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
            Customize ({chosenArtists.length})
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
  filtered: PoolArtist[];
  chosen: Set<string>;
  chosenCount: number;
  toggle: (id: string) => void;
  addHeadliners: () => void;
  clearAll: () => void;
  hasStages: boolean;
  allStages: string[];
  allGenres: string[];
  stageFilter: string;
  setStageFilter: (s: string) => void;
  genreFilter: string;
  setGenreFilter: (s: string) => void;
  sort: Sort;
  setSort: (s: Sort) => void;
  palettes: Palette[];
  applyPalette: (p: Palette) => void;
  bg: string;
  setBg: (s: string) => void;
  fg: string;
  setFg: (s: string) => void;
  download: () => void;
}

function Controls(p: ControlsProps) {
  const atMax = p.chosenCount >= MAX_ARTISTS;
  return (
    <div>
      <h1 className="text-display-md text-white">Make your wallpaper</h1>
      <p className="mt-1 text-body text-[color:var(--text-muted)]">
        Pick the artists you want — up to {MAX_ARTISTS}. {p.festival.name}.
      </p>

      {/* Shortcuts */}
      <div className="mt-5 flex flex-wrap gap-2">
        <button
          onClick={p.addHeadliners}
          className="rounded-full bg-accent px-4 py-2 text-label font-semibold uppercase tracking-wide text-black"
        >
          + Add all headliners
        </button>
        <button
          onClick={p.clearAll}
          className="rounded-full border border-[color:var(--border)] px-4 py-2 text-label font-semibold uppercase tracking-wide text-[color:var(--text-muted)] hover:text-[color:var(--text)]"
        >
          Clear
        </button>
        <span className="ml-auto self-center text-label text-[color:var(--text-muted)]">
          {p.chosenCount}/{MAX_ARTISTS}
        </span>
      </div>

      {/* Filters + sort */}
      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
        {p.hasStages && p.allStages.length > 0 && (
          <Select label="Stage" value={p.stageFilter} onChange={p.setStageFilter}
            options={["all", ...p.allStages]} />
        )}
        {p.allGenres.length > 0 && (
          <Select label="Genre" value={p.genreFilter} onChange={p.setGenreFilter}
            options={["all", ...p.allGenres]} />
        )}
        <Select label="Sort" value={p.sort} onChange={(v) => p.setSort(v as Sort)}
          options={["popularity", "alpha"]} />
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

      {/* Artist checklist */}
      <ul className="mt-5 max-h-[40vh] divide-y divide-white/10 overflow-y-auto rounded-2xl border border-[color:var(--border)]">
        {p.filtered.map((a) => {
          const on = p.chosen.has(a.id);
          return (
            <li key={a.id}>
              <label
                className={`flex cursor-pointer items-center gap-3 px-4 py-2.5 ${
                  !on && atMax ? "opacity-40" : ""
                }`}
              >
                <input
                  type="checkbox"
                  checked={on}
                  disabled={!on && atMax}
                  onChange={() => p.toggle(a.id)}
                  className="h-4 w-4 accent-[var(--accent)]"
                />
                <span className="flex-1 truncate text-body text-[color:var(--text)]">{a.name}</span>
                {a.headliner && <span className="text-[10px] font-bold uppercase text-accent">★</span>}
                {a.stages[0] && (
                  <span className="max-w-[40%] truncate text-label text-[color:var(--text-muted)]">{a.stages[0]}</span>
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
    <label className="flex flex-col gap-1 text-label text-[color:var(--text-muted)]">
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
  names: string[];
  bg: string;
  fg: string;
  accent: string;
}

function paint(ctx: CanvasRenderingContext2D, a: PaintArgs) {
  const { festival, names, bg, fg, accent } = a;

  // Background + a soft accent glow up top (sits behind the clock zone).
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);
  const glow = ctx.createRadialGradient(W / 2, H * 0.18, 60, W / 2, H * 0.18, W * 0.9);
  glow.addColorStop(0, hexA(accent, 0.22));
  glow.addColorStop(1, hexA(accent, 0));
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, W, H);

  ctx.textAlign = "center";

  // ── Zone boundaries ──
  const TOP_ZONE = H / 3; // clock / widgets — kept clear
  const BOTTOM_ZONE = (H * 2) / 3; // OS UI overlays below this — kept clear

  // Festival header sits at the top of the CENTER zone (clear of the clock).
  let y = TOP_ZONE + 70;
  ctx.fillStyle = accent;
  ctx.font = "600 38px 'Space Grotesk', system-ui, sans-serif";
  ctx.fillText("MY LINEUP", W / 2, y);
  y += 78;
  ctx.fillStyle = fg;
  ctx.font = "700 64px 'Space Grotesk', system-ui, sans-serif";
  for (const line of wrap(ctx, festival.name.toUpperCase(), W * 0.84).slice(0, 2)) {
    ctx.fillText(line, W / 2, y);
    y += 70;
  }

  // ── Center zone: the artist list, vertically centered, auto-scaled ──
  const listTop = y + 40;
  const listBottom = BOTTOM_ZONE + H * 0.14; // allow the list into the upper bottom-zone, still clear of the home bar
  const n = names.length;
  if (n > 0) {
    const band = listBottom - listTop;
    const lh = Math.min(118, band / n);
    let fontSize = Math.round(lh * 0.62);
    // Shrink to the widest name so nothing clips at the gutters.
    const fit = () => {
      ctx.font = `600 ${fontSize}px Inter, system-ui, sans-serif`;
      return names.every((nm) => ctx.measureText(nm).width <= W * 0.86);
    };
    while (fontSize > 18 && !fit()) fontSize -= 2;
    ctx.font = `600 ${fontSize}px Inter, system-ui, sans-serif`;

    const blockH = lh * n;
    let ly = listTop + (band - blockH) / 2 + lh / 2;
    ctx.textBaseline = "middle";
    ctx.fillStyle = fg;
    for (const nm of names) {
      ctx.fillText(truncate(ctx, nm, W * 0.88), W / 2, ly);
      ly += lh;
    }
  } else {
    ctx.fillStyle = hexA(fg, 0.5);
    ctx.font = "500 40px Inter, system-ui, sans-serif";
    ctx.textBaseline = "middle";
    ctx.fillText("Pick artists to build your wallpaper", W / 2, (listTop + listBottom) / 2);
  }

  // ── Branding: Soundcheck wordmark, bottom-center in the safe zone ──
  ctx.textBaseline = "alphabetic";
  const brandY = H * 0.9;
  // Small mark dot in the brand gradient, then the wordmark.
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
