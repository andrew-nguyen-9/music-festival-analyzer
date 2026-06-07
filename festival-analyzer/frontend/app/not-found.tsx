import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-[80vh] flex-col items-center justify-center px-5 text-center">
      <p className="text-display-xl text-accent">404</p>
      <h1 className="mt-2 text-heading font-semibold text-white">
        We couldn&apos;t find that page
      </h1>
      <p className="mt-3 max-w-md text-body text-[color:var(--text-muted)]">
        The festival or artist you&apos;re looking for may not be in the
        database yet.
      </p>
      <Link
        href="/"
        className="mt-8 rounded-full bg-accent px-6 py-3 text-label font-semibold uppercase tracking-wide text-black transition-transform hover:scale-105"
      >
        Back to festivals
      </Link>
    </div>
  );
}
