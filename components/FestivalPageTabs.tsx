"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import LineupByDay from "./LineupByDay";
import LineupByPopularity from "./LineupByPopularity";
import LineupGrid from "./LineupGrid";
import FestivalTBD from "./FestivalTBD";
import ScheduleBoard from "./ScheduleBoard";
import LineupAnalysis from "./LineupAnalysis";
import Reveal from "./Reveal";
import { accentGradient } from "@/lib/festival-theme";
import type { Festival, LineupEntry } from "@/lib/types";
import type { FestivalState } from "@/lib/format";

interface Props {
  festival: Festival;
  lineup: LineupEntry[];
  state: FestivalState;
}

type Tab = "lineup" | "schedule" | "analysis";
type ViewMode = "grid" | "list";

export default function FestivalPageTabs({ festival, lineup, state }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("lineup");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");

  if (state === "tbd") return <FestivalTBD festival={festival} />;

  const hasLineup   = lineup.length > 0;
  const hasSchedule = lineup.some((e) => e.day != null && e.set_time_start != null);

  function tab(t: Tab) {
    return (
      <button
        onClick={() => setActiveTab(t)}
        className={`relative px-5 py-3.5 text-label font-semibold uppercase tracking-wide transition-colors ${
          activeTab === t
            ? "text-white after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:bg-accent"
            : "text-white/40 hover:text-white/70"
        }`}
      >
        {t}
      </button>
    );
  }

  return (
    <>
      {/* Tab bar */}
      <div className="mx-auto max-w-wide px-5 pt-4 md:px-8">
        <div className="flex items-end border-b border-white/15">
          {tab("lineup")}
          {tab("schedule")}
          {hasLineup && tab("analysis")}

          {/* Grid / list toggle — only on lineup tab */}
          {activeTab === "lineup" && hasLineup && state !== "passed" && (
            <div className="ml-auto mb-1 flex gap-1">
              <ViewBtn
                active={viewMode === "grid"}
                onClick={() => setViewMode("grid")}
                title="Grid view"
              >
                <GridIcon />
              </ViewBtn>
              <ViewBtn
                active={viewMode === "list"}
                onClick={() => setViewMode("list")}
                title="List view"
              >
                <ListIcon />
              </ViewBtn>
            </div>
          )}
        </div>
      </div>

      {/* ── Lineup tab ── */}
      {activeTab === "lineup" && (
        <>
          {state === "passed" && <LineupGrid lineup={lineup} />}
          {state === "schedule" && viewMode === "grid" && <LineupByDay lineup={lineup} />}
          {state === "schedule" && viewMode === "list" && <LineupListView lineup={lineup} />}
          {state === "lineup"   && viewMode === "grid" && <LineupByPopularity lineup={lineup} />}
          {state === "lineup"   && viewMode === "list" && <LineupListView lineup={lineup} />}
        </>
      )}

      {/* ── Schedule tab ── */}
      {activeTab === "schedule" && (
        <section className="mx-auto max-w-wide px-5 py-10 md:px-8">
          <Reveal>
            <h2 className="mb-8 text-display-lg text-white">Schedule</h2>
          </Reveal>
          {hasSchedule ? (
            <ScheduleBoard lineup={lineup} />
          ) : (
            <ScheduleTBD />
          )}
        </section>
      )}

      {/* ── Analysis tab ── */}
      {activeTab === "analysis" && hasLineup && (
        <section className="mx-auto max-w-wide px-5 py-10 md:px-8">
          <Reveal>
            <h2 className="mb-8 text-display-lg text-white">Lineup Analysis</h2>
          </Reveal>
          <LineupAnalysis lineup={lineup} />
        </section>
      )}
    </>
  );
}

// ── Headliner computation (mirrors LineupByDay logic) ────────────

function computeHeadlinerIds(entries: LineupEntry[]): Set<string> {
  const byStage = new Map<string, LineupEntry[]>();
  for (const e of entries) {
    const key = e.stage ?? "__none__";
    if (!byStage.has(key)) byStage.set(key, []);
    byStage.get(key)!.push(e);
  }
  const ids = new Set<string>();
  for (const [, acts] of byStage) {
    const timed = acts.filter((e) => e.set_time_start);
    if (timed.length < 2) continue;
    const sorted = [...timed].sort((a, b) =>
      (b.set_time_start ?? "").localeCompare(a.set_time_start ?? ""),
    );
    ids.add(sorted[0].id); // closing act only
  }
  return ids;
}

// ── Compact list view ─────────────────────────────────────────────

function LineupListView({ lineup }: { lineup: LineupEntry[] }) {
  // Group by day first (days ascending), then within each day sort latest → earliest
  const grouped = new Map<string, LineupEntry[]>();
  for (const e of lineup) {
    const key = e.day ?? "TBD";
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(e);
  }

  // Sort within each day: popularity first, tiebreak by time descending
  for (const [key, entries] of grouped) {
    grouped.set(
      key,
      entries.sort((a, b) => {
        const popDiff = (b.artist.spotify_popularity ?? 0) - (a.artist.spotify_popularity ?? 0);
        if (popDiff !== 0) return popDiff;
        const ta = a.set_time_start ?? "";
        const tb = b.set_time_start ?? "";
        if (ta && tb) return tb.localeCompare(ta);
        return 0;
      }),
    );
  }

  const days = [...grouped.keys()].sort((a, b) => {
    if (a === "TBD") return 1;
    if (b === "TBD") return -1;
    return a.localeCompare(b);
  });

  // Compute headliners per day using the same last-2-per-stage rule
  const headlinerIdsByDay = new Map<string, Set<string>>();
  for (const [day, entries] of grouped) {
    headlinerIdsByDay.set(day, computeHeadlinerIds(entries));
  }

  function fmtDay(iso: string) {
    if (iso === "TBD") return "TBD";
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
  }

  return (
    <section className="mx-auto max-w-wide px-5 py-10 md:px-8">
      <div className="space-y-8">
        {days.map((day) => (
          <div key={day}>
            {days.length > 1 && (
              <h3 className="mb-3 text-label uppercase tracking-widest text-white/40">
                {fmtDay(day)}
              </h3>
            )}
            <div className="divide-y divide-white/[0.06] overflow-hidden rounded-xl border border-white/10">
              {grouped.get(day)!.map((entry) => (
                <ListRow
                  key={entry.id}
                  entry={entry}
                  isHeadliner={headlinerIdsByDay.get(day)?.has(entry.id) ?? false}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function ListRow({ entry, isHeadliner }: { entry: LineupEntry; isHeadliner: boolean }) {
  const { artist } = entry;
  const img = artist.image_url ?? artist.header_image_url;

  return (
    <Link
      href={`/artist/${artist.slug}`}
      className="flex items-center gap-4 bg-surface-elevated px-4 py-3 transition-colors hover:bg-white/5"
    >
      <div className="relative h-11 w-11 shrink-0 overflow-hidden rounded-lg">
        {img ? (
          <Image
            src={img}
            alt={artist.name}
            fill
            sizes="44px"
            className="object-cover"
          />
        ) : (
          <div
            className="h-full w-full"
            style={{ backgroundImage: accentGradient(null) }}
          />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate font-semibold text-white">{artist.name}</p>
        {artist.genres?.length > 0 && (
          <p className="truncate text-[11px] uppercase tracking-wide text-white/40">
            {artist.genres.slice(0, 2).join(" · ")}
          </p>
        )}
      </div>

      <div className="shrink-0 text-right">
        {entry.stage && (
          <p className="text-[11px] text-accent/70">{entry.stage}</p>
        )}
        {entry.set_time_start && (
          <p className="text-[11px] text-white/40">
            {entry.set_time_start.slice(0, 5)}
            {entry.set_time_end ? `–${entry.set_time_end.slice(0, 5)}` : ""}
          </p>
        )}
      </div>

      {isHeadliner && (
        <span className="shrink-0 rounded-full bg-accent/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-accent">
          Headliner
        </span>
      )}
    </Link>
  );
}

// ── Schedule TBD ─────────────────────────────────────────────────

function ScheduleTBD() {
  return (
    <div className="flex flex-col items-center gap-6 py-16 text-center">
      <div className="relative flex h-24 w-24 items-center justify-center">
        <div className="absolute inset-0 animate-ping rounded-full bg-accent/10" />
        <div className="absolute inset-2 rounded-full bg-accent/10" />
        <CalendarIcon />
      </div>
      <div>
        <h3 className="text-heading font-semibold text-white">Schedule Coming Soon</h3>
        <p className="mt-2 max-w-sm text-body text-white/50">
          The day-by-day stage schedule hasn't been announced yet. Check back closer to the festival.
        </p>
      </div>
    </div>
  );
}

// ── UI helpers ────────────────────────────────────────────────────

function ViewBtn({
  active, onClick, title, children,
}: {
  active: boolean; onClick: () => void; title: string; children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`rounded-lg p-1.5 transition-colors ${
        active ? "bg-white/15 text-white" : "text-white/40 hover:text-white/70"
      }`}
    >
      {children}
    </button>
  );
}

function GridIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
      <rect x="1" y="1" width="6" height="6" rx="1" />
      <rect x="9" y="1" width="6" height="6" rx="1" />
      <rect x="1" y="9" width="6" height="6" rx="1" />
      <rect x="9" y="9" width="6" height="6" rx="1" />
    </svg>
  );
}

function ListIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M5 4h9M5 8h9M5 12h9M2 4h.01M2 8h.01M2 12h.01" />
    </svg>
  );
}

function CalendarIcon() {
  return (
    <svg
      width="36" height="36"
      viewBox="0 0 24 24"
      className="relative text-accent"
      fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"
    >
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M8 2v4M16 2v4M3 10h18" />
    </svg>
  );
}
