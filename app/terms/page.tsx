import type { Metadata } from "next";

export const metadata: Metadata = { title: "Terms" };

export default function TermsPage() {
  return (
    <main className="mx-auto max-w-3xl px-5 py-24 md:px-8">
      <h1 className="mb-8 text-display-lg text-white">Terms</h1>
      <div className="space-y-5 text-body-lg leading-relaxed text-[color:var(--text-muted)]">
        <p>
          Soundcheck is provided as-is, for informational and entertainment
          purposes. Lineups, dates, and artist data are aggregated from third-party
          sources and may be incomplete, estimated, or out of date — always confirm
          details with the official festival before making plans.
        </p>
        <p>
          Artist names, festival names, and logos are the property of their
          respective owners. Music data and imagery are surfaced under the terms of
          their source APIs (Spotify, MusicBrainz, Wikipedia, Deezer, Ticketmaster,
          Unsplash); Soundcheck claims no ownership over them.
        </p>
        <p>
          By using the site you agree that the project and its creator are not
          liable for decisions made based on this data.
        </p>
      </div>
    </main>
  );
}
