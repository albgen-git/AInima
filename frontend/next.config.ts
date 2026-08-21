import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

// next/image richiede un allow-list esplicito degli host esterni da cui
// caricare immagini — qui l'host del backend (foto profilo/partner
// ideale, servite da StaticFiles su /photos, v. backend/main.py).
const apiUrl = new URL(process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8010");

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: apiUrl.protocol.replace(":", "") as "http" | "https",
        hostname: apiUrl.hostname,
        port: apiUrl.port,
        pathname: "/photos/**",
      },
    ],
  },
};

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

export default withNextIntl(nextConfig);
