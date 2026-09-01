import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

// next/image richiede un allow-list esplicito degli host esterni da cui
// caricare immagini — qui l'host del backend (foto profilo/partner
// ideale, servite da StaticFiles su /photos, v. backend/main.py) PIÙ il
// dominio pubblico R2 (foto del pool demo migrato + upload live dopo il
// passaggio a R2, v. backend/services/photo_storage.py). Bug reale
// trovato dal vivo (v. CLAUDE.md): senza il secondo pattern, next/image
// rifiuta silenziosamente qualunque foto R2 su Proposta/Rubrica (le due
// uniche pagine che usano <Image> invece di <img> — v. photoUrl() in
// lib/api/index.ts per lo stesso problema già risolto lato URL string).
const apiUrl = new URL(process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8010");
const r2PublicUrl = new URL(
  process.env.NEXT_PUBLIC_R2_PUBLIC_BASE_URL ?? "https://pub-efe6351402e141f5b50e53cf7c6499fa.r2.dev"
);

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: apiUrl.protocol.replace(":", "") as "http" | "https",
        hostname: apiUrl.hostname,
        port: apiUrl.port,
        pathname: "/photos/**",
      },
      {
        protocol: r2PublicUrl.protocol.replace(":", "") as "http" | "https",
        hostname: r2PublicUrl.hostname,
        pathname: "/**",
      },
    ],
  },
};

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

export default withNextIntl(nextConfig);
