/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // Django exige la barra final: el proxy /api/proxy/... no debe quitarla.
  skipTrailingSlashRedirect: true,
  // TanStack Query publica código moderno (métodos privados de clase, Chrome 84+). Se transpila para que la app
  // funcione también en celulares con el WebView/navegador sin actualizar (p. ej. Android 7 a 11 sin Play Store).
  transpilePackages: ["@tanstack/react-query", "@tanstack/query-core"],
  async headers() {
    return [
      { source: "/sw.js", headers: [
        { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
        { key: "Service-Worker-Allowed", value: "/" },
      ] },
      { source: "/manifest.webmanifest", headers: [{ key: "Content-Type", value: "application/manifest+json" }] },
    ];
  },
  poweredByHeader: false,
  // Sin el optimizador de imágenes de Next: las fotos se sirven tal cual. Menos superficie de ataque (el optimizador
  // fue la fuente de varios avisos de seguridad) y no hace falta instalar «sharp» en la imagen.
  images: { unoptimized: true },
};

module.exports = nextConfig;
