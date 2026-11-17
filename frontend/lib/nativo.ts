/**
 * Detección de la app Android (Capacitor). La app carga este mismo sitio dentro de un WebView y Capacitor le
 * inyecta `window.Capacitor` con los plugins nativos (notificaciones push, etc.). En un navegador normal no
 * existe, y todo lo que dependa de ello simplemente no se activa.
 */
interface PluginPush {
  requestPermissions: () => Promise<{ receive: string }>;
  register: () => Promise<void>;
  addListener: (evento: string, fn: (dato: never) => void) => Promise<{ remove: () => Promise<void> }>;
}
interface CapacitorGlobal {
  isNativePlatform?: () => boolean;
  getPlatform?: () => string;
  Plugins?: { PushNotifications?: PluginPush };
}

export function capacitor(): CapacitorGlobal | null {
  if (typeof window === "undefined") return null;
  return (window as unknown as { Capacitor?: CapacitorGlobal }).Capacitor ?? null;
}

export const esAppNativa = (): boolean => !!capacitor()?.isNativePlatform?.();

/**
 * El APK declara en su user-agent («DUBSSPush») si se compiló con Firebase (google-services.json). Sin Firebase,
 * llamar a `PushNotifications.register()` cierra la app por una excepción nativa que JavaScript no puede
 * capturar, así que solo se intenta cuando el APK dice que está listo.
 */
export const pushDisponible = (): boolean => esAppNativa() && typeof navigator !== "undefined" && /DUBSSPush/.test(navigator.userAgent);
export const pushNativo = (): PluginPush | null => capacitor()?.Plugins?.PushNotifications ?? null;
