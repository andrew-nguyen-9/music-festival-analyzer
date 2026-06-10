import type { Festival } from "@/lib/types";
import { formatDateRange } from "@/lib/format";

interface Props {
  festival: Festival;
}

export default function FestivalPassedBanner({ festival }: Props) {
  const year = festival.start_date
    ? new Date(festival.start_date + "T00:00:00").getFullYear()
    : null;

  return (
    <div className="w-full border-b border-white/10 bg-white/5 px-5 py-4 md:px-8">
      <div className="mx-auto flex max-w-wide items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl" aria-hidden>
            👋
          </span>
          <div>
            <p className="text-label font-semibold uppercase tracking-widest text-white/50">
              See you next year
            </p>
            <p className="mt-0.5 text-body text-white/35">
              {festival.name}
              {year ? ` ${year}` : ""} has wrapped
              {festival.start_date
                ? ` · ${formatDateRange(festival.start_date, festival.end_date)}`
                : ""}
            </p>
          </div>
        </div>
        <span className="shrink-0 rounded-full border border-white/15 px-3 py-1 text-label text-white/40">
          Past edition
        </span>
      </div>
    </div>
  );
}
