import Link from "next/link";
import SearchCommand from "@/components/SearchCommand";
import Logo from "@/components/Logo";
import ThemeToggle from "@/components/ThemeToggle";
import SettingsPanel from "@/components/SettingsPanel";

/**
 * Global top nav. Transparent over heroes, sticky. The Soundcheck mark keeps
 * its fixed brand gradient on every page (see Logo.tsx).
 */
export default function Nav() {
  return (
    <header className="fixed inset-x-0 top-0 z-50">
      <div className="mx-auto flex max-w-wide items-center justify-between px-5 py-4 md:px-8">
        <Link
          href="/"
          className="group transition-transform hover:scale-[1.03]"
          aria-label="Soundcheck — home"
        >
          <Logo className="h-7 w-auto" />
        </Link>
        <nav className="flex items-center gap-6 text-label uppercase tracking-[0.12em] text-[color:var(--text-muted)]">
          <Link
            href="/"
            className="transition-colors hover:text-[color:var(--text)]"
          >
            Festivals
          </Link>
          <Link
            href="/about"
            className="hidden transition-colors hover:text-[color:var(--text)] sm:inline"
          >
            About
          </Link>
          <SearchCommand />
          <ThemeToggle />
          <SettingsPanel />
        </nav>
      </div>
    </header>
  );
}
