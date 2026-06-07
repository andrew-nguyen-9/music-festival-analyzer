import Link from "next/link";

/**
 * Global top nav. Transparent over heroes, sticky. Festival pages render
 * it inside a FestivalThemeStyle wrapper so the wordmark dot picks up the
 * festival accent.
 */
export default function Nav() {
  return (
    <header className="fixed inset-x-0 top-0 z-50">
      <div className="mx-auto flex max-w-wide items-center justify-between px-5 py-4 md:px-8">
        <Link
          href="/"
          className="group flex items-center gap-2 text-label uppercase tracking-[0.18em] text-white"
        >
          <span className="inline-block h-2 w-2 rounded-full bg-accent transition-transform group-hover:scale-125" />
          Festival&nbsp;Analyzer
        </Link>
        <nav className="flex items-center gap-6 text-label uppercase tracking-[0.12em] text-[color:var(--text-muted)]">
          <Link href="/" className="transition-colors hover:text-white">
            Festivals
          </Link>
          <a
            href="https://github.com"
            className="hidden transition-colors hover:text-white sm:inline"
            rel="noreferrer"
          >
            About
          </a>
        </nav>
      </div>
    </header>
  );
}
