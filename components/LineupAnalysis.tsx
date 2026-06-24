"use client";

import { useMemo } from "react";
import Link from "next/link";
import { formatCount } from "@/lib/format";
import type { LineupEntry } from "@/lib/types";

// ── Tier definitions ─────────────────────────────────────────────

const POP_TIERS = [
  { label: "Icon",         min: 85, bar: "bg-yellow-400",  badge: "bg-yellow-400/15 text-yellow-300" },
  { label: "Superstar",    min: 70, bar: "bg-orange-400",  badge: "bg-orange-400/15 text-orange-300" },
  { label: "Mainstream",   min: 55, bar: "bg-accent",      badge: "bg-accent/15 text-accent" },
  { label: "Established",  min: 40, bar: "bg-sky-400",     badge: "bg-sky-400/15 text-sky-300" },
  { label: "Emerging",     min: 0,  bar: "bg-white/25",    badge: "bg-white/10 text-white/50" },
] as const;

const AUDIENCE_TIERS = [
  { label: "Mega",         sub: "10M+ followers", min: 10_000_000, bar: "bg-yellow-400" },
  { label: "Large",        sub: "1M – 10M",       min: 1_000_000,  bar: "bg-orange-400" },
  { label: "Mid-tier",     sub: "100K – 1M",      min: 100_000,    bar: "bg-accent" },
  { label: "Underground",  sub: "Under 100K",      min: 0,          bar: "bg-white/25" },
] as const;

function popTier(score: number) {
  return POP_TIERS.find((t) => score >= t.min) ?? POP_TIERS[POP_TIERS.length - 1];
}

function avgPopLabel(avg: number) {
  if (avg >= 80) return "Superstar lineup";
  if (avg >= 65) return "Mainstream-heavy";
  if (avg >= 50) return "Well-established";
  if (avg >= 35) return "Discovery-focused";
  return "Underground";
}

// ── Headliner computation ────────────────────────────────────────

function computeHeadlinerIds(lineup: LineupEntry[]): Set<string> {
  const hasSchedule = lineup.some((e) => e.set_time_start);
  if (hasSchedule) {
    // Last act per (day × stage) = headliner
    const byDayStage = new Map<string, LineupEntry[]>();
    for (const e of lineup) {
      if (!e.set_time_start) continue;
      const key = `${e.day ?? "TBD"}__${e.stage ?? "none"}`;
      if (!byDayStage.has(key)) byDayStage.set(key, []);
      byDayStage.get(key)!.push(e);
    }
    const ids = new Set<string>();
    for (const [, acts] of byDayStage) {
      if (acts.length < 2) continue;
      const last = [...acts].sort((a, b) =>
        (b.set_time_start ?? "").localeCompare(a.set_time_start ?? ""),
      )[0];
      ids.add(last.id);
    }
    return ids;
  }
  // No schedule: top 2 by popularity
  const ids = new Set<string>();
  [...lineup]
    .sort((a, b) => (b.artist.spotify_popularity ?? 0) - (a.artist.spotify_popularity ?? 0))
    .slice(0, 2)
    .forEach((e) => ids.add(e.id));
  return ids;
}

// ── Component ────────────────────────────────────────────────────

interface Props { lineup: LineupEntry[] }

export default function LineupAnalysis({ lineup }: Props) {
  const headlinerIds = useMemo(() => computeHeadlinerIds(lineup), [lineup]);
  const headliners   = useMemo(() => lineup.filter((e) => headlinerIds.has(e.id)), [lineup, headlinerIds]);

  // ── Genre counts ──────────────────────────────────────────────
  const genreCounts = useMemo(() => {
    const m = new Map<string, number>();
    for (const e of lineup) {
      for (const g of e.artist.genres ?? []) m.set(g, (m.get(g) ?? 0) + 1);
    }
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [lineup]);

  // ── Popularity tier distribution ─────────────────────────────
  const popWithData  = lineup.filter((e) => e.artist.spotify_popularity != null);
  const popTierCounts = useMemo(() => {
    return POP_TIERS.map((tier, i) => {
      const max = i === 0 ? 101 : POP_TIERS[i - 1].min;
      const count = popWithData.filter(
        (e) => (e.artist.spotify_popularity ?? 0) >= tier.min && (e.artist.spotify_popularity ?? 0) < max,
      ).length;
      return { ...tier, count };
    });
  }, [popWithData]);

  const avgPop = useMemo(() => {
    if (popWithData.length === 0) return null;
    return Math.round(popWithData.reduce((s, e) => s + (e.artist.spotify_popularity ?? 0), 0) / popWithData.length);
  }, [popWithData]);

  // ── Audience tier distribution ────────────────────────────────
  const audWithData = lineup.filter((e) => e.artist.spotify_followers != null);
  const audTierCounts = useMemo(() => {
    return AUDIENCE_TIERS.map((tier, i) => {
      const max = i === 0 ? Infinity : AUDIENCE_TIERS[i - 1].min;
      const count = audWithData.filter(
        (e) => (e.artist.spotify_followers ?? 0) >= tier.min && (e.artist.spotify_followers ?? 0) < max,
      ).length;
      return { ...tier, count };
    });
  }, [audWithData]);

  const totalFollowers = useMemo(
    () => audWithData.reduce((s, e) => s + (e.artist.spotify_followers ?? 0), 0),
    [audWithData],
  );

  // ── Stage breakdown ───────────────────────────────────────────
  const stageCounts = useMemo(() => {
    const m = new Map<string, number>();
    for (const e of lineup) if (e.stage) m.set(e.stage, (m.get(e.stage) ?? 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [lineup]);

  // Headliner per stage (most popular headliner at each stage)
  const headlinerPerStage = useMemo(() => {
    const m = new Map<string, LineupEntry>();
    for (const e of headliners) {
      if (!e.stage) continue;
      const cur = m.get(e.stage);
      if (!cur || (e.artist.spotify_popularity ?? 0) > (cur.artist.spotify_popularity ?? 0)) {
        m.set(e.stage, e);
      }
    }
    return [...m.entries()].sort((a, b) => b[1].artist.spotify_popularity! - a[1].artist.spotify_popularity!);
  }, [headliners]);

  // ── Discovery picks ───────────────────────────────────────────
  const hiddenGems = useMemo(
    () =>
      [...lineup]
        .filter((e) => e.artist.spotify_popularity != null && (e.artist.spotify_popularity) < 45)
        .sort((a, b) => (b.artist.spotify_popularity ?? 0) - (a.artist.spotify_popularity ?? 0))
        .slice(0, 6),
    [lineup],
  );

  // ── Top by popularity + followers ────────────────────────────
  const topByPop = useMemo(
    () =>
      [...lineup]
        .filter((e) => e.artist.spotify_popularity != null)
        .sort((a, b) => (b.artist.spotify_popularity ?? 0) - (a.artist.spotify_popularity ?? 0))
        .slice(0, 8),
    [lineup],
  );

  const maxStage = stageCounts[0]?.[1] ?? 1;
  const maxGenre = genreCounts[0]?.[1] ?? 1;
  const maxAud   = audTierCounts[0]?.count ?? 1;

  const emergingPct = popWithData.length > 0
    ? Math.round((popWithData.filter((e) => (e.artist.spotify_popularity ?? 0) < 40).length / popWithData.length) * 100)
    : null;

  return (
    <div className="space-y-12">

      {/* ── Hero stats ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <StatBox value={String(lineup.length)} label="Artists" />
        <StatBox value={String(headliners.length)} label="Headliners" />
        <StatBox value={String(stageCounts.length)} label="Stages" />
        <StatBox value={String(genreCounts.length)} label="Genres" />
        {avgPop != null && (
          <StatBox value={String(avgPop)} label={avgPopLabel(avgPop)} accent />
        )}
      </div>

      {/* ── Popularity tier breakdown (full-width) ───────────────── */}
      {popWithData.length > 0 && (
        <div>
          <SectionLabel>Popularity tiers</SectionLabel>
          <p className="mb-4 text-[12px] text-white/40">
            Based on Spotify popularity score (0–100) · {popWithData.length} artists with data
          </p>
          {/* Stacked bar */}
          <div className="mb-4 flex h-4 w-full overflow-hidden rounded-full">
            {popTierCounts.map((t) =>
              t.count > 0 ? (
                <div
                  key={t.label}
                  title={`${t.label}: ${t.count}`}
                  className={`${t.bar} transition-all`}
                  style={{ width: `${(t.count / popWithData.length) * 100}%` }}
                />
              ) : null,
            )}
          </div>
          {/* Legend */}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            {popTierCounts.map((t) => (
              <div key={t.label} className="flex items-center gap-2 rounded-lg border border-white/10 bg-surface-elevated px-3 py-2.5">
                <span className={`h-2 w-2 shrink-0 rounded-full ${t.bar}`} />
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold text-white">{t.label}</p>
                  <p className="text-[10px] text-white/40">{t.count} artists · {popWithData.length > 0 ? Math.round((t.count / popWithData.length) * 100) : 0}%</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Audience size distribution ───────────────────────────── */}
      {audWithData.length > 0 && (
        <div>
          <SectionLabel>Audience size</SectionLabel>
          <p className="mb-4 text-[12px] text-white/40">
            By Spotify follower count · {formatCount(totalFollowers)} combined followers
            {emergingPct != null && ` · ${emergingPct}% emerging acts`}
          </p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {audTierCounts.map((t) => (
              <div key={t.label} className="rounded-xl border border-white/10 bg-surface-elevated p-4">
                <div className="mb-3 flex items-start justify-between">
                  <div>
                    <p className="font-semibold text-white">{t.label}</p>
                    <p className="text-[11px] text-white/40">{t.sub}</p>
                  </div>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold text-black ${t.bar}`}>
                    {t.count}
                  </span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                  <div
                    className={`h-full rounded-full ${t.bar} transition-all`}
                    style={{ width: `${maxAud > 0 ? (t.count / audTierCounts.reduce((s, x) => s + x.count, 0)) * 100 : 0}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── 3-col grid ──────────────────────────────────────────── */}
      <div className="grid gap-8 md:grid-cols-2 xl:grid-cols-3">

        {/* Headliners */}
        {headliners.length > 0 && (
          <div>
            <SectionLabel>Headliners</SectionLabel>
            <div className="space-y-2">
              {headliners.map((e) => {
                const tier = popTier(e.artist.spotify_popularity ?? 0);
                return (
                  <ArtistRow key={e.id} entry={e}>
                    <span className="text-accent">★</span>
                    <div className="flex min-w-0 flex-1 items-center justify-between gap-2">
                      <span className="truncate font-medium text-white">{e.artist.name}</span>
                      <div className="flex shrink-0 items-center gap-1.5">
                        {e.artist.spotify_popularity != null && (
                          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${tier.badge}`}>
                            {tier.label}
                          </span>
                        )}
                        {e.stage && <span className="text-[11px] text-white/35">{e.stage}</span>}
                      </div>
                    </div>
                  </ArtistRow>
                );
              })}
            </div>
          </div>
        )}

        {/* Genre mix */}
        {genreCounts.length > 0 && (
          <div>
            <SectionLabel>Genre mix · {genreCounts.length} genres</SectionLabel>
            <div className="space-y-2">
              {genreCounts.slice(0, 12).map(([genre, count]) => (
                <div key={genre}>
                  <div className="mb-1 flex justify-between">
                    <span className="text-[12px] capitalize text-white/80">{genre}</span>
                    <span className="text-[12px] text-white/35">{count}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                    <div
                      className="h-full rounded-full bg-accent transition-all"
                      style={{ width: `${(count / maxGenre) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top 8 by popularity */}
        {topByPop.length > 0 && (
          <div>
            <SectionLabel>Top artists by popularity</SectionLabel>
            <div className="space-y-1.5">
              {topByPop.map((e, i) => {
                const tier = popTier(e.artist.spotify_popularity ?? 0);
                return (
                  <ArtistRow key={e.id} entry={e}>
                    <span className="w-5 shrink-0 text-center text-[11px] text-white/30">{i + 1}</span>
                    <div className="flex min-w-0 flex-1 items-center justify-between gap-2">
                      <span className="truncate text-white">{e.artist.name}</span>
                      <div className="flex shrink-0 items-center gap-1.5">
                        <span className="text-[11px] font-semibold text-white/60">{e.artist.spotify_popularity}</span>
                        <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-bold ${tier.badge}`}>
                          {tier.label}
                        </span>
                      </div>
                    </div>
                  </ArtistRow>
                );
              })}
            </div>
          </div>
        )}

        {/* Headliner per stage */}
        {headlinerPerStage.length > 0 && (
          <div>
            <SectionLabel>Headliner by stage</SectionLabel>
            <div className="space-y-2">
              {headlinerPerStage.map(([stage, e]) => (
                <ArtistRow key={stage} entry={e}>
                  <div className="flex min-w-0 flex-1 items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate font-medium text-white">{e.artist.name}</p>
                      <p className="text-[11px] text-white/40">{stage}</p>
                    </div>
                    {e.artist.spotify_followers != null && (
                      <span className="shrink-0 text-[11px] text-white/40">
                        {formatCount(e.artist.spotify_followers)}
                      </span>
                    )}
                  </div>
                </ArtistRow>
              ))}
            </div>
          </div>
        )}

        {/* Discovery picks */}
        {hiddenGems.length > 0 && (
          <div>
            <SectionLabel>Discovery picks · under the radar</SectionLabel>
            <div className="space-y-1.5">
              {hiddenGems.map((e) => (
                <ArtistRow key={e.id} entry={e}>
                  <span className="text-[14px]">🔍</span>
                  <div className="flex min-w-0 flex-1 items-center justify-between gap-2">
                    <span className="truncate text-white">{e.artist.name}</span>
                    {e.artist.genres?.[0] && (
                      <span className="shrink-0 text-[11px] capitalize text-white/40">
                        {e.artist.genres[0]}
                      </span>
                    )}
                  </div>
                </ArtistRow>
              ))}
            </div>
          </div>
        )}

        {/* Stage breakdown */}
        {stageCounts.length > 0 && (
          <div>
            <SectionLabel>Stage breakdown</SectionLabel>
            <div className="space-y-2.5">
              {stageCounts.map(([stage, count]) => {
                const stageHeadliner = headlinerPerStage.find(([s]) => s === stage)?.[1];
                return (
                  <div key={stage}>
                    <div className="mb-1 flex justify-between">
                      <div>
                        <span className="text-[12px] text-white/80">{stage}</span>
                        {stageHeadliner && (
                          <span className="ml-2 text-[11px] text-accent/70">
                            closes: {stageHeadliner.artist.name}
                          </span>
                        )}
                      </div>
                      <span className="text-[12px] text-white/35">{count}</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full rounded-full bg-accent/50 transition-all"
                        style={{ width: `${(count / maxStage) * 100}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

      </div>

      {/* ── Age data note ────────────────────────────────────────── */}
      <div className="flex items-start gap-4 rounded-xl border border-dashed border-white/15 bg-white/[0.02] p-5">
        <span className="mt-0.5 text-xl">📅</span>
        <div>
          <p className="font-semibold text-white/70">Artist age breakdown coming soon</p>
          <p className="mt-1 text-[12px] leading-relaxed text-white/40">
            Age and career era data (birth year, years active) isn&apos;t in the pipeline yet.
            To enable this, add a <code className="rounded bg-white/10 px-1 text-white/60">birth_year</code> column
            to the <code className="rounded bg-white/10 px-1 text-white/60">artists</code> table and enrich it
            via the artist enricher — then a generational breakdown (Gen Z / Millennial / Gen X) and career
            length distribution will appear here automatically.
          </p>
        </div>
      </div>

    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <p className="mb-3 text-label uppercase tracking-widest text-white/35">{children}</p>;
}

function StatBox({ value, label, accent }: { value: string; label: string; accent?: boolean }) {
  return (
    <div className={`rounded-xl border px-4 py-4 text-center ${accent ? "border-accent/30 bg-accent/5" : "border-white/10 bg-surface-elevated"}`}>
      <p className={`text-display-md font-semibold ${accent ? "text-accent" : "text-white"}`}>{value}</p>
      <p className="mt-1 text-[11px] uppercase tracking-widest text-white/40">{label}</p>
    </div>
  );
}

function ArtistRow({ entry, children }: { entry: LineupEntry; children?: React.ReactNode }) {
  return (
    <Link
      href={`/artist/${entry.artist.slug}`}
      className="flex items-center gap-3 rounded-xl border border-white/10 bg-surface-elevated px-3 py-2.5 transition-colors hover:border-white/20 hover:bg-white/5"
    >
      {children}
    </Link>
  );
}
