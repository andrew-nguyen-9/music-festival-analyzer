import Link from "next/link";
import Logo from "@/components/Logo";
import A11yShortcutButton from "@/components/A11yShortcutButton";

const GITHUB = "https://github.com/andrew-nguyen-9/soundcheck";
const CREATOR = "https://an9.dev";
const X = "https://x.com/an9dev";

/**
 * Global footer (v4.5), rendered once in app/layout.tsx. Theme-aware via CSS
 * variables. Groups: site nav, legal/attribution, creator/social, plus the
 * accessibility-panel shortcut.
 */
export default function Footer() {
  return (
    <footer className="mt-20 border-t border-[color:var(--border)] bg-surface-elevated">
      <div className="mx-auto grid max-w-wide gap-10 px-5 py-14 md:grid-cols-[1.4fr,1fr,1fr,1fr] md:px-8">
        {/* Brand */}
        <div>
          <Logo className="h-7 w-auto" />
          <p className="mt-4 max-w-xs text-body text-[color:var(--text-muted)]">
            Artist and lineup intelligence for US music festivals — from
            Lollapalooza to 200+ festivals.
          </p>
        </div>

        <FooterGroup title="Explore">
          <FooterLink href="/">Festivals</FooterLink>
          <FooterLink href="/about">About</FooterLink>
          <FooterLink href="/search">Search</FooterLink>
          <FooterLink href="/status">Status</FooterLink>
        </FooterGroup>

        <FooterGroup title="Info">
          <FooterLink href="/privacy">Privacy</FooterLink>
          <FooterLink href="/terms">Terms</FooterLink>
          <li className="pt-1 text-[12px] leading-relaxed text-[color:var(--text-muted)]">
            Data from Spotify, MusicBrainz, Wikipedia, Deezer, Ticketmaster &amp;
            Unsplash.
          </li>
        </FooterGroup>

        <FooterGroup title="Creator">
          <FooterLink href={CREATOR} external>
            an9.dev
          </FooterLink>
          <FooterLink href={GITHUB} external>
            GitHub
          </FooterLink>
          <FooterLink href={X} external>
            X / Twitter
          </FooterLink>
          <li>
            <A11yShortcutButton className="text-body text-[color:var(--text-muted)] transition-colors hover:text-[color:var(--text)]" />
          </li>
        </FooterGroup>
      </div>

      <div className="border-t border-[color:var(--border)]">
        <div className="mx-auto flex max-w-wide flex-col items-start justify-between gap-2 px-5 py-6 text-[12px] text-[color:var(--text-muted)] sm:flex-row sm:items-center md:px-8">
          <span>© {new Date().getFullYear()} Soundcheck · Built with Next.js + Supabase</span>
          <span>Made by an9.dev</span>
        </div>
      </div>
    </footer>
  );
}

function FooterGroup({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <p className="mb-3 text-label uppercase tracking-[0.12em] text-[color:var(--text-muted)]">
        {title}
      </p>
      <ul className="space-y-2.5">{children}</ul>
    </div>
  );
}

function FooterLink({
  href,
  external,
  children,
}: {
  href: string;
  external?: boolean;
  children: React.ReactNode;
}) {
  const cls =
    "text-body text-[color:var(--text-muted)] transition-colors hover:text-[color:var(--text)]";
  return (
    <li>
      {external ? (
        <a href={href} target="_blank" rel="noreferrer" className={cls}>
          {children} ↗
        </a>
      ) : (
        <Link href={href} className={cls}>
          {children}
        </Link>
      )}
    </li>
  );
}
