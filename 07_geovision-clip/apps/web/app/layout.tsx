import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Providers } from "@/components/providers";
import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "GeoVisionCLIP Cali",
  description:
    "Predicción de calidad del aire en Santiago de Cali combinando Sentinel-2, Sentinel-5P, MODIS y ERA5-Land. Prototipo MVP.",
  applicationName: "GeoVisionCLIP",
  authors: [{ name: "Equipo GeoVisionCLIP-Cali" }],
  generator: "Next.js 16",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="es"
      suppressHydrationWarning
      className={`${GeistSans.variable} ${GeistMono.variable}`}
    >
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
