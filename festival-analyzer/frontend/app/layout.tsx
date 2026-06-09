import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import CustomCursor from "@/components/CustomCursor";

export const metadata: Metadata = {
  title: {
    default: "Festival Analyzer — US Music Festival Lineup Intelligence",
    template: "%s · Festival Analyzer",
  },
  description:
    "Artist and lineup intelligence for US music festivals. Search by artist, genre, city, or vibe — from Lollapalooza to 200+ festivals.",
  metadataBase: new URL("https://festival-analyzer.vercel.app"),
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        {/* Inter loaded at runtime (graceful fallback to system-ui offline). */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap"
        />
      </head>
      <body className="min-h-screen bg-surface font-sans text-white antialiased">
        {/* Film-grain texture overlay (creative-dev T19) */}
        <div className="grain-overlay" aria-hidden />
        <CustomCursor />
        <Nav />
        <main>{children}</main>
        <footer className="border-t border-white/10 px-5 py-10 text-label text-[color:var(--text-muted)] md:px-8">
          <div className="mx-auto max-w-wide">
            Festival Analyzer · Data from Spotify, Apple Music &amp; Unsplash ·
            Built with Next.js + Supabase
          </div>
        </footer>
      </body>
    </html>
  );
}
