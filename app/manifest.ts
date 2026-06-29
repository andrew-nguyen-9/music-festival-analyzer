import type { MetadataRoute } from "next";

// PWA manifest (v2.7.1) — installable, dark theme, accent-tinted.
// ponytail: single SVG icon for now (scales to any size + maskable). Add raster
// PNG icons only if a target platform rejects SVG manifest icons.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Soundcheck",
    short_name: "Festivals",
    description:
      "Artist and lineup intelligence for US music festivals — usable offline in the field.",
    start_url: "/",
    display: "standalone",
    background_color: "#0A0A0A",
    theme_color: "#0A0A0A",
    icons: [
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "any",
      },
    ],
  };
}
