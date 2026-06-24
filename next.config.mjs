/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      // Unsplash CDN (festival + media photos)
      { protocol: "https", hostname: "images.unsplash.com" },
      { protocol: "https", hostname: "plus.unsplash.com" },
      // Deezer artist images (fallback when Spotify is unavailable)
      { protocol: "https", hostname: "cdn-images.dzcdn.net" },
      { protocol: "https", hostname: "e-cdns-images.dzcdn.net" },
      // Ticketmaster artist/event images
      { protocol: "https", hostname: "**.ticketm.net" },
      { protocol: "https", hostname: "**.ticketmaster.com" },
      // Spotify artist/album art
      { protocol: "https", hostname: "i.scdn.co" },
      { protocol: "https", hostname: "mosaic.scdn.co" },
      // Apple Music artwork
      { protocol: "https", hostname: "is1-ssl.mzstatic.com" },
      { protocol: "https", hostname: "is2-ssl.mzstatic.com" },
      { protocol: "https", hostname: "is3-ssl.mzstatic.com" },
      { protocol: "https", hostname: "is4-ssl.mzstatic.com" },
      { protocol: "https", hostname: "is5-ssl.mzstatic.com" },
    ],
  },
};

export default nextConfig;
