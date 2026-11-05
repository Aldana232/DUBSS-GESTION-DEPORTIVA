import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { RegistrarServiceWorker } from "@/components/pwa/RegistrarServiceWorker";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "DUBSS — Sistema de Gestión Deportiva",
  description: "Sistema inteligente de gestión deportiva de la Dirección Universitaria de Bienestar Social y Salud (UAGRM)",
  icons: { icon: "/logo-dubss.png", apple: "/icons/apple-touch-icon.png" },
  manifest: "/manifest.webmanifest",
  applicationName: "DUBSS",
  appleWebApp: { capable: true, title: "DUBSS", statusBarStyle: "black-translucent" },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, viewportFit: "cover", themeColor: "#d21115" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className={`${inter.variable} font-sans`}>
        <Providers>{children}</Providers>
        <RegistrarServiceWorker />
      </body>
    </html>
  );
}
