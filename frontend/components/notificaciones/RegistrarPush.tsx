"use client";
import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/hooks/useAuth";
import { pushService } from "@/lib/api/services";
import { pushDisponible, pushNativo } from "@/lib/nativo";
import { rutaDeNotificacion } from "@/lib/notificaciones";

/**
 * Solo en la app Android: pide permiso de notificaciones, obtiene el token del celular (Firebase) y lo
 * registra en el servidor; al tocar una notificación abre la pantalla que corresponde.
 * En un navegador normal no hace nada. Si el APK se compiló sin Firebase tampoco hace nada (intentarlo cerraría la
 * app) y el usuario sigue recibiendo sus avisos en la campana (y por correo o WhatsApp si los activó).
 * El rol JUGADOR es de solo lectura y no registra el celular.
 */
export function RegistrarPush() {
  const { rol, usuario } = useAuth();
  const router = useRouter();
  const hecho = useRef<number | null>(null);

  useEffect(() => {
    if (!usuario || rol === "JUGADOR" || !pushDisponible() || hecho.current === usuario.id) return;
    const push = pushNativo();
    if (!push) return;
    hecho.current = usuario.id;
    const quitar: Array<() => Promise<void>> = [];
    let activo = true;

    (async () => {
      try {
        const registro = await push.addListener("registration", ((t: { value: string }) => {
          void pushService.registrar(t.value).catch(() => undefined);
        }) as never);
        const toque = await push.addListener("pushNotificationActionPerformed", ((a: { notification?: { data?: Record<string, unknown> } }) => {
          router.push(rutaDeNotificacion(a.notification?.data));
        }) as never);
        quitar.push(() => registro.remove(), () => toque.remove());
        if (!activo) return;
        const permiso = await push.requestPermissions();
        if (permiso.receive === "granted") await push.register();
      } catch {
        /* sin Firebase o sin permiso: la bandeja de la app sigue funcionando */
      }
    })();

    return () => { activo = false; quitar.forEach((q) => void q().catch(() => undefined)); hecho.current = null; };
  }, [usuario, rol, router]);

  return null;
}
