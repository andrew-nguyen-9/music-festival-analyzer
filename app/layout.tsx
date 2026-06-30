import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";
import Nav from "@/components/Nav";

// Self-hosted via next/font (v2.10.2) — no render-blocking Google stylesheet,
// no layout shift, `swap` so text paints immediately. Exposes the same CSS vars
// globals.css already references.
const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-inter",
  display: "swap",
});
const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display",
  display: "swap",
});
import CustomCursor from "@/components/CustomCursor";
import Footer from "@/components/Footer";
import MotionProvider from "@/components/MotionProvider";
import ServiceWorkerRegistrar from "@/components/ServiceWorkerRegistrar";
import OfflineIndicator from "@/components/OfflineIndicator";
import WebVitals from "@/components/WebVitals";

export const metadata: Metadata = {
  title: {
    default: "Soundcheck — US Music Festival Lineup Intelligence",
    template: "%s · Soundcheck",
  },
  description:
    "Artist and lineup intelligence for US music festivals. Search by artist, genre, city, or vibe — from Lollapalooza to 200+ festivals.",
  metadataBase: new URL("https://soundcheck.an9.dev"),
};

export const viewport = {
  themeColor: "#0A0A0A",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${spaceGrotesk.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/* Apply theme + a11y settings before first paint to avoid a flash. Dark
            is the brand default; stored prefs (Nav toggle / a11y panel) override.
            Mirrors lib/settings.ts — keep class/key names in sync. */}
        <script
          dangerouslySetInnerHTML={{
            __html:
              "(function(){try{var d=document.documentElement,g=function(k){return localStorage.getItem(k)};var t=g('theme');d.dataset.theme=(t==='light'||t==='dark')?t:'dark';if(g('a11y-contrast')==='on')d.classList.add('hc');if(g('a11y-motion')==='on')d.classList.add('rm');var cb=g('a11y-colorblind');if(cb&&cb!=='none')d.classList.add('cb-'+cb);d.classList.add('fs-'+(g('a11y-font')||'m'));}catch(e){document.documentElement.dataset.theme='dark';}})();",
          }}
        />
      </head>
      <body className="min-h-screen bg-surface font-sans text-[color:var(--text)] antialiased">
        {/* Film-grain texture overlay (creative-dev T19) */}
        <div className="grain-overlay" aria-hidden />
        <WebVitals />
        <OfflineIndicator />
        <ServiceWorkerRegistrar />
        <CustomCursor />
        <MotionProvider>
          <Nav />
          <main>{children}</main>
        </MotionProvider>
        <Footer />
      </body>
    </html>
  );
}
