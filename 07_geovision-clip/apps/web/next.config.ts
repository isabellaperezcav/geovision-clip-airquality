import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Salida autocontenida para empaquetado en Docker (server.js + dependencias minimas).
  output: "standalone",
};

export default nextConfig;
