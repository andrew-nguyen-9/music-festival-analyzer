"use client";

import { useState, useMemo } from "react";
import Image from "next/image";
import Link from "next/link";
import Reveal from "./Reveal";
import { accentGradient } from "@/lib/festival-theme";
import { hasMultipleWeekends, groupLineupByDay } from "@/lib/format";
import type { LineupEntry } from "@/lib/types";

interface Props {
  lineup: LineupEntry[];
}

function formatDayLabel(iso: string): string {
  if (iso === "TBD") return "TBD";
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function weekendNumber(iso: string, firstDate: string): 1 | 2 {
  const diff = (new Date(iso + "T00:00:00").getTime() - new Date(firstDate + "T00:00:00").getTime()) / 86_400_000;
  return diff < 7 ? 1 : 2;
}

export default function LineupByDay({ lineup }: Props) {
  const allDays = useMemo(() => {
    const days = [...lineup].map((e) => e.day);
    return days;
  }, [lineup]);

  const showWeekends = useMemo(() => hasMultipleWeekends(allDays), [allDays]);

  const dayMap = useMemo(() => groupLineupByDay(lineup), [lineup]);
  const sortedDays = useMemo(
    () =>
      [...dayMap.keys()].sort((a, b) => {
        if (a === "TBD") return 1;
        if (b === "TBD") return -1;
        return a.localeCompare(b);
      }),
    [dayMap],
  );

  const firstDate = sortedDays.find((d) => d !== "TBD") ?? "TBD";

  // Weekend grouping
  const weekend1Days = useMemo(
    () => sortedDays.filter((d) => d === "TBD" || weekendNumber(d, firstDate) === 1),
    [sortedDays, firstDate],
  );
  const weekend2Days = useMemo(
    () => sortedDays.filter((d) => d !== "TBD" && weekendNumber(d, firstDate) === 2),
    [sortedDays, firstDate],
  );

  const [activeWeekend, setActiveWeekend] = useState<1 | 2>(1);
  const visibleDays = showWeekends
    ? activeWeekend === 1 ? weekend1Days : weekend2Days
    : sortedDays;

  const [activeDay, setActiveDay] = useState<string>(visibleDays[0] ?? "TBD");

  // Reset day selection when weekend changes
  const handleWeekend = (w: 1 | 2) => {
    setActiveWeekend(w);
    const days = w === 1 ? weekend1Days : weekend2Days;
    setActiveDay(days[0] ?? "TBD");
  };

  const dayLineup = useMemo(
    () =>
      [...(dayMap.get(activeDay) ?? [])].sort((a, b) => {
        if (a.is_headliner !== b.is_headliner) return a.is_headliner ? -1 : 1;
        const ta = a.set_time_start ?? "";
        const tb = b.set_time_start ?? "";
        if (ta && tb) return ta.localeCompare(tb);
        return (b.artist.spotify_popularity ?? 0) - (a.artist.spotify_popularity ?? 0);
      }),
    [dayMap, activeDay],
  );

  const TabButton = ({
    label,
    active,
    onClick,
  }: {
    label: string;
    active: boolean;
    onClick: () => void;
  }) => (
    <button
      onClick={onClick}
      className={`rounded-full px-4 py-2 text-label font-semibold transition-all ${
        active
          ? "bg-accent text-black"
          : "border border-white/20 text-white/60 hover:border-white/40 hover:text-white"
      }`}
    >
      {label}
    </button>
  );

  return (
    <section className="mx-auto max-w-wide px-5 py-16 md:px-8">
      <Reveal>
        <h2 className="mb-8 text-display-lg text-white">Lineup</h2>
      </Reveal>

      {/* Weekend tabs (only if two distinct weekends with different lineups) */}
      {showWeekends && (
        <div className="mb-6 flex gap-3">
          <TabButton label="Weekend 1" active={activeWeekend === 1} onClick={() => handleWeekend(1)} />
          <TabButton label="Weekend 2" active={activeWeekend === 2} onClick={() => handleWeekend(2)} />
        </div>
      )}

      {/* Day tabs */}
      <div className="mb-10 flex flex-wrap gap-2">
        {visibleDays.map((day) => (
          <TabButton
            key={day}
            label={formatDayLabel(day)}
            active={activeDay === day}
            onClick={() => setActiveDay(day)}
          />
        ))}
      </div>

      {/* Lineup grid for selected day */}
      {dayLineup.length === 0 ? (
        <p className="text-body text-white/40">No artists scheduled for this day yet.</p>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {dayLineup.map((entry, i) => (
            <Reveal key={entry.id} delay={Math.min(i * 0.03, 0.4)}>
              <DayArtistTile entry={entry} />
            </Reveal>
          ))}
        </div>
      )}
    </section>
  );
}

function DayArtistTile({ entry }: { entry: LineupEntry }) {
  const { artist } = entry;
  const img = artist.image_url ?? artist.header_image_url;

  return (
    <Link
      href={`/artist/${artist.slug}`}
      className="group relative block overflow-hidden rounded-xl border border-white/10 bg-surface-elevated"
    >
      <div className="relative aspect-square w-full overflow-hidden">
        {img ? (
          <Image
            src={img}
            alt={artist.name}
            fill
            sizes="(max-width: 640px) 50vw, 25vw"
            className="object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div
            className="h-full w-full"
            style={{ backgroundImage: accentGradient(null) }}
            aria-hidden
          />
        )}
        <div className="hero-scrim absolute inset-0 opacity-90" />
        {entry.is_headliner && (
          <span className="absolute left-2 top-2 rounded-full bg-accent px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-black">
            Headliner
          </span>
        )}
        {entry.set_time_start && (
          <span className="absolute right-2 top-2 rounded-full bg-black/60 px-2 py-0.5 text-[10px] font-medium text-white/80">
            {entry.set_time_start.slice(0, 5)}
          </span>
        )}
        <div className="absolute inset-x-0 bottom-0 p-3">
          <p className={`font-semibold leading-tight text-white ${entry.is_headliner ? "text-display-md" : "text-body-lg"}`}>
            {artist.name}
          </p>
          {artist.genres?.length > 0 && (
            <p className="mt-0.5 truncate text-[11px] uppercase tracking-wide text-white/60">
              {artist.genres.slice(0, 2).join(" · ")}
            </p>
          )}
          {entry.stage && (
            <p className="mt-0.5 truncate text-[10px] text-accent/80">{entry.stage}</p>
          )}
        </div>
      </div>
    </Link>
  );
}
