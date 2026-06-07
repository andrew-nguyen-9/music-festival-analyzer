import type { ReactNode } from "react";

interface Props {
  title: string;
  hint?: string;
  icon?: ReactNode;
}

/**
 * Consistent empty state for sections with no data yet (media, social,
 * fun facts, lineup). Designed to look intentional, not broken.
 */
export default function EmptyState({ title, hint, icon }: Props) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-white/10 bg-surface-elevated/60 px-6 py-14 text-center">
      <div className="mb-3 text-accent/80" aria-hidden>
        {icon ?? <DefaultIcon />}
      </div>
      <p className="text-heading font-semibold text-white">{title}</p>
      {hint && (
        <p className="mt-2 max-w-sm text-body text-[color:var(--text-muted)]">
          {hint}
        </p>
      )}
    </div>
  );
}

function DefaultIcon() {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M9 10h.01M15 10h.01M9 15c.83.67 1.9 1 3 1s2.17-.33 3-1" />
    </svg>
  );
}
