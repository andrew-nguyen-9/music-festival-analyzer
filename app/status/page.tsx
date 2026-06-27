import { getRecentIngestionRuns } from "@/lib/queries";

// Pipeline observability dashboard (v3.11) — reads the ingestion_runs run-log
// (public-read RLS). Shows recent runs + a freshness summary off the same data
// the v3.1 gate enforces. ISR: refresh every 5 min.
export const revalidate = 300;

const STATUS_COLOR: Record<string, string> = {
  success: "text-emerald-400",
  partial: "text-amber-400",
  error: "text-red-400",
  running: "text-sky-400",
};

const STALE_DAYS = 30;

export default async function StatusPage() {
  const runs = await getRecentIngestionRuns(120);

  // Per-festival freshness: newest successful run, flagged stale past STALE_DAYS.
  const latestSuccess = new Map<string, string>();
  for (const r of runs) {
    if (r.status === "success" && r.festival_slug) {
      const prev = latestSuccess.get(r.festival_slug);
      if (!prev || r.started_at > prev) latestSuccess.set(r.festival_slug, r.started_at);
    }
  }
  const cutoff = Date.now() - STALE_DAYS * 86400_000;
  const stale = [...latestSuccess.entries()].filter(([, ts]) => Date.parse(ts) < cutoff);
  const errors = runs.filter((r) => r.status === "error").length;

  return (
    <main className="mx-auto min-h-screen max-w-wide px-5 pt-28 md:px-8">
      <h1 className="mb-2 text-display font-semibold text-white">Pipeline status</h1>
      <p className="mb-8 text-white/50">
        Ingestion run-log — what ran, when, and how fresh the catalog is.
      </p>

      <div className="mb-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat label="Runs shown" value={runs.length} />
        <Stat label="Festivals tracked" value={latestSuccess.size} />
        <Stat label={`Stale (>${STALE_DAYS}d)`} value={stale.length} warn={stale.length > 0} />
        <Stat label="Errors" value={errors} warn={errors > 0} />
      </div>

      {runs.length === 0 ? (
        <p className="text-white/50">No ingestion runs recorded yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-white/10">
          <table className="w-full text-sm">
            <thead className="bg-white/5 text-left text-xs uppercase tracking-[0.12em] text-white/40">
              <tr>
                <th className="px-4 py-3">Festival</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Started</th>
                <th className="px-4 py-3 text-right">+Upserted</th>
                <th className="px-4 py-3 text-right">Skipped</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {runs.map((r, i) => (
                <tr key={i} className="text-white/80">
                  <td className="px-4 py-2.5">{r.festival_slug ?? "—"}</td>
                  <td className={`px-4 py-2.5 font-medium ${STATUS_COLOR[r.status] ?? "text-white/60"}`}>
                    {r.status}
                  </td>
                  <td className="px-4 py-2.5 text-white/50">
                    {new Date(r.started_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{r.rows_upserted ?? 0}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{r.rows_skipped ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}

function Stat({ label, value, warn }: { label: string; value: number; warn?: boolean }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className={`text-3xl font-semibold ${warn ? "text-amber-400" : "text-white"}`}>
        {value}
      </div>
      <div className="mt-1 text-xs uppercase tracking-[0.12em] text-white/40">{label}</div>
    </div>
  );
}
