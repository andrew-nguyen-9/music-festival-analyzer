"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import type { LineupEntry } from "@/lib/types";
import {
  timeToMinutes,
  fmtSetTime as fmtTime,
  fmtDayLabel as fmtDay,
} from "@/lib/format";

const PX_PER_MIN = 2; // vertical density: 2px per minute of set

// One colour per stage slot (up to 8)
const STAGE_COLORS = [
  { bg: "bg-violet-500/75 hover:bg-violet-400/90", ring: "ring-violet-400/40" },
  { bg: "bg-sky-500/75 hover:bg-sky-400/90",       ring: "ring-sky-400/40" },
  { bg: "bg-emerald-500/75 hover:bg-emerald-400/90", ring: "ring-emerald-400/40" },
  { bg: "bg-amber-500/75 hover:bg-amber-400/90",   ring: "ring-amber-400/40" },
  { bg: "bg-pink-500/75 hover:bg-pink-400/90",     ring: "ring-pink-400/40" },
  { bg: "bg-cyan-500/75 hover:bg-cyan-400/90",     ring: "ring-cyan-400/40" },
  { bg: "bg-orange-500/75 hover:bg-orange-400/90", ring: "ring-orange-400/40" },
  { bg: "bg-lime-500/75 hover:bg-lime-400/90",     ring: "ring-lime-400/40" },
];

interface Props { lineup: LineupEntry[] }

export default function ScheduleBoard({ lineup }: Props) {
  const dayMap = useMemo(() => {
    const m = new Map<string, LineupEntry[]>();
    for (const e of lineup) {
      if (!e.day || !e.set_time_start) continue;
      if (!m.has(e.day)) m.set(e.day, []);
      m.get(e.day)!.push(e);
    }
    return m;
  }, [lineup]);

  const days = useMemo(() => [...dayMap.keys()].sort(), [dayMap]);
  const [activeDay, setActiveDay] = useState(days[0] ?? "");
  const [mobileStageIdx, setMobileStageIdx] = useState(0);

  const entries = useMemo(() => dayMap.get(activeDay) ?? [], [dayMap, activeDay]);

  // Stages ordered by artist count (busiest first)
  const stages = useMemo(() => {
    const cnt = new Map<string, number>();
    for (const e of entries) if (e.stage) cnt.set(e.stage, (cnt.get(e.stage) ?? 0) + 1);
    return [...cnt.entries()].sort((a, b) => b[1] - a[1]).map(([s]) => s);
  }, [entries]);

  const { dayStart, dayEnd } = useMemo(() => {
    let lo = 12 * 60, hi = 22 * 60;
    for (const e of entries) {
      if (e.set_time_start) lo = Math.min(lo, timeToMinutes(e.set_time_start));
      if (e.set_time_end)   hi = Math.max(hi, timeToMinutes(e.set_time_end));
    }
    return { dayStart: lo, dayEnd: hi };
  }, [entries]);

  const totalMin = dayEnd - dayStart;
  const boardH   = totalMin * PX_PER_MIN;
  const hourTicks = Array.from({ length: Math.ceil(totalMin / 60) + 1 }, (_, i) => i * 60)
    .filter((m) => m <= totalMin);

  if (days.length === 0) {
    return (
      <p className="py-8 text-center text-body text-white/40">
        No schedule data available yet.
      </p>
    );
  }

  return (
    <div>
      {/* Day tabs */}
      <div className="mb-5 flex flex-wrap gap-2">
        {days.map((d) => (
          <button
            key={d}
            onClick={() => { setActiveDay(d); setMobileStageIdx(0); }}
            className={`rounded-full px-4 py-2 text-label font-semibold transition-all ${
              activeDay === d
                ? "bg-accent text-black"
                : "border border-white/20 text-white/60 hover:border-white/40 hover:text-white"
            }`}
          >
            {fmtDay(d)}
          </button>
        ))}
      </div>

      {/* Stage picker (mobile only) */}
      <div className="mb-3 flex flex-wrap gap-1.5 sm:hidden">
        {stages.map((s, i) => (
          <button
            key={s}
            onClick={() => setMobileStageIdx(i)}
            className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wide transition-all ${
              mobileStageIdx === i
                ? "bg-white/20 text-white"
                : "text-white/40 hover:text-white/70"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Board */}
      <div className="overflow-x-auto rounded-xl border border-white/10 bg-black/20">
        <div
          className="flex"
          style={{ minWidth: `${stages.length * 180 + 56}px` }}
        >
          {/* Time ruler */}
          <div className="sticky left-0 z-10 w-14 shrink-0 border-r border-white/10 bg-surface">
            <div className="h-9 border-b border-white/10" />
            <div className="relative" style={{ height: `${boardH}px` }}>
              {hourTicks.map((m) => (
                <div
                  key={m}
                  className="absolute left-0 right-0"
                  style={{ top: `${m * PX_PER_MIN}px` }}
                >
                  <span className="block px-2 text-[10px] leading-none text-white/30">
                    {fmtTime(`${Math.floor((dayStart + m) / 60) % 24}:${String((dayStart + m) % 60).padStart(2, "0")}`)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Stage columns */}
          {stages.map((stage, si) => {
            const col = STAGE_COLORS[si % STAGE_COLORS.length];
            const colEntries = entries.filter((e) => e.stage === stage && e.set_time_start);

            return (
              <div
                key={stage}
                className={`flex-1 border-r border-white/10 last:border-r-0 ${
                  si !== mobileStageIdx ? "hidden sm:block" : ""
                }`}
              >
                {/* Stage header */}
                <div className="flex h-9 items-center justify-center border-b border-white/10 px-2">
                  <span className="truncate text-[11px] font-semibold uppercase tracking-wider text-white/50">
                    {stage}
                  </span>
                </div>

                {/* Timeline */}
                <div className="relative" style={{ height: `${boardH}px` }}>
                  {/* Hour grid lines */}
                  {hourTicks.map((m) => (
                    <div
                      key={m}
                      className="absolute inset-x-0 border-t border-white/[0.06]"
                      style={{ top: `${m * PX_PER_MIN}px` }}
                    />
                  ))}

                  {/* Artist blocks */}
                  {colEntries.map((entry) => {
                    const startMin = timeToMinutes(entry.set_time_start!) - dayStart;
                    const rawEnd   = entry.set_time_end
                      ? timeToMinutes(entry.set_time_end) - dayStart
                      : startMin + 60;
                    const duration = Math.max(rawEnd - startMin, 30);
                    const top    = startMin * PX_PER_MIN;
                    const height = duration * PX_PER_MIN;

                    return (
                      <Link
                        key={entry.id}
                        href={`/artist/${entry.artist.slug}`}
                        title={`${entry.artist.name} · ${entry.set_time_start?.slice(0, 5)}–${entry.set_time_end?.slice(0, 5) ?? "?"}`}
                        className={`absolute inset-x-1 overflow-hidden rounded-lg px-2 py-1.5 transition-all ${col.bg} ${
                          entry.is_headliner ? `ring-1 ${col.ring}` : ""
                        }`}
                        style={{ top: `${top}px`, height: `${height}px` }}
                      >
                        <p className="truncate text-[11px] font-semibold leading-tight text-white">
                          {entry.artist.name}
                        </p>
                        {height >= 42 && entry.set_time_start && (
                          <p className="text-[10px] text-white/60">
                            {fmtTime(entry.set_time_start)}
                          </p>
                        )}
                        {entry.is_headliner && (
                          <span className="absolute right-1 top-1 text-[9px] text-white/80">★</span>
                        )}
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-3">
        {stages.map((s, i) => {
          const col = STAGE_COLORS[i % STAGE_COLORS.length];
          return (
            <div key={s} className="flex items-center gap-1.5">
              <span className={`h-2.5 w-2.5 rounded-sm ${col.bg.split(" ")[0]}`} />
              <span className="text-[11px] text-white/50">{s}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
