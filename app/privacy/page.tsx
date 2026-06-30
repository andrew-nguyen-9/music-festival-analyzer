import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy" };

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-3xl px-5 py-24 md:px-8">
      <h1 className="mb-8 text-display-lg text-white">Privacy</h1>
      <div className="space-y-5 text-body-lg leading-relaxed text-[color:var(--text-muted)]">
        <p>
          Soundcheck is an independent project. It does not have user accounts and
          does not collect personal information. Your theme and accessibility
          preferences are stored only in your browser&apos;s localStorage — they
          never leave your device and are not sent to any server.
        </p>
        <p>
          Festival and artist data is aggregated from public sources (Spotify,
          MusicBrainz, Wikipedia, Deezer, Ticketmaster, Unsplash). Anonymous,
          aggregate performance metrics (Web Vitals) may be collected to keep the
          site fast; they are not tied to any individual.
        </p>
        <p>
          Questions? Reach out via{" "}
          <a
            href="https://an9.dev"
            target="_blank"
            rel="noreferrer"
            className="text-accent hover:underline"
          >
            an9.dev
          </a>
          .
        </p>
      </div>
    </main>
  );
}
