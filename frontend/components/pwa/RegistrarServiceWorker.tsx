"use client";
import { useEffect } from "react";

/**
 * Registra el service worker solo en producción (en desarrollo estorba: guardaría versiones viejas) y, de paso,
 * elimina cualquier registro previo cuando se trabaja en modo desarrollo.
 */
export function RegistrarServiceWorker() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    if (process.env.NODE_ENV !== "production") {
      navigator.serviceWorker.getRegistrations().then((regs) => regs.forEach((r) => r.unregister())).catch(() => undefined);
      return;
    }
    navigator.serviceWorker.register("/sw.js", { scope: "/" })
      .then(() => navigator.serviceWorker.ready)
      .then((registro) => {
        // Le pide al service worker guardar lo que esta página ya cargó, para poder abrirla sin conexión.
        const urls = performance.getEntriesByType("resource").map((r) => new URL(r.name).pathname).filter((u) => u.startsWith("/_next/static/"));
        if (window.location.pathname === "/planilla") urls.push("/planilla");
        registro.active?.postMessage({ tipo: "PRECARGAR", urls: Array.from(new Set(urls)) });
      })
      .catch(() => undefined);
  }, []);
  return null;
}
