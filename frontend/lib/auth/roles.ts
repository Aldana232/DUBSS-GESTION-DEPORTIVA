/**
 * Configuración de roles y rutas (F4-07 / F5). Ocultar menús o rutas por rol es solo
 * experiencia de usuario: la seguridad real la hace la API (cada endpoint valida el rol).
 */
export type Rol = "SUPERADMIN" | "ADMIN_DUBSS" | "ORGANIZADOR" | "DELEGADO" | "JUGADOR";

export const ROL_ETIQUETA: Record<Rol, string> = {
  SUPERADMIN: "Superadministrador",
  ADMIN_DUBSS: "Administrador DUBSS",
  ORGANIZADOR: "Organizador",
  DELEGADO: "Delegado",
  JUGADOR: "Jugador",
};

export const ROLES_GESTION: Rol[] = ["SUPERADMIN", "ADMIN_DUBSS", "ORGANIZADOR"];
export const ROLES_ADMIN: Rol[] = ["SUPERADMIN", "ADMIN_DUBSS"];

/** Pantalla de inicio de cada rol. */
export const ROLE_HOME: Record<Rol, string> = {
  SUPERADMIN: "/gestion",
  ADMIN_DUBSS: "/gestion",
  ORGANIZADOR: "/gestion",
  DELEGADO: "/delegado",
  JUGADOR: "/jugador",
};

export type Permiso =
  | "campeonato:gestionar"
  | "fixture:generar"
  | "resultado:registrar"
  | "reporte:exportar"
  | "ml:consultar";

const GESTION: Permiso[] = ["campeonato:gestionar", "fixture:generar", "resultado:registrar", "reporte:exportar", "ml:consultar"];

export const PERMISOS_POR_ROL: Record<Rol, Permiso[]> = {
  SUPERADMIN: GESTION,
  ADMIN_DUBSS: GESTION,
  ORGANIZADOR: GESTION,
  DELEGADO: ["ml:consultar"],
  JUGADOR: [],
};

export type IconoMenu =
  | "inicio" | "campeonatos" | "inscripciones" | "fixture" | "predicciones" | "quejas"
  | "reportes" | "catalogos" | "usuarios" | "bitacora" | "equipos" | "calendario" | "asistente" | "notificaciones" | "planilla";

export interface ItemMenu {
  href: string;
  label: string;
  /** Clave de ícono; components/layout/iconos.ts la traduce (así el middleware no carga lucide). */
  icono: IconoMenu;
  /** Si es true, solo está activo con la ruta exacta (ej.: el inicio del panel). */
  exacto?: boolean;
}

const G = "/gestion";
const D = "/delegado";

const GESTION_BASE: ItemMenu[] = [
  { href: G, label: "Inicio", icono: "inicio", exacto: true },
  { href: `${G}/campeonatos`, label: "Campeonatos", icono: "campeonatos" },
  { href: `${G}/inscripciones`, label: "Inscripciones", icono: "inscripciones" },
  { href: `${G}/fixture`, label: "Fixture", icono: "fixture" },
  { href: `${G}/predicciones`, label: "Inteligencia artificial", icono: "predicciones" },
  { href: `${G}/quejas`, label: "Quejas", icono: "quejas" },
  { href: `${G}/reportes`, label: "Reportes", icono: "reportes" },
  { href: "/planilla", label: "Planilla móvil", icono: "planilla" },
  { href: `${G}/asistente`, label: "Asistente", icono: "asistente" },
  { href: `${G}/notificaciones`, label: "Avisos", icono: "notificaciones" },
];

const SOLO_ADMIN: ItemMenu[] = [
  { href: `${G}/catalogos`, label: "Catálogos", icono: "catalogos" },
  { href: `${G}/usuarios`, label: "Usuarios", icono: "usuarios" },
  { href: `${G}/bitacora`, label: "Bitácora", icono: "bitacora" },
];

export const NAV_BY_ROLE: Record<Rol, ItemMenu[]> = {
  SUPERADMIN: [...GESTION_BASE, ...SOLO_ADMIN],
  ADMIN_DUBSS: [...GESTION_BASE, ...SOLO_ADMIN],
  ORGANIZADOR: GESTION_BASE,
  DELEGADO: [
    { href: D, label: "Inicio", icono: "inicio", exacto: true },
    { href: `${D}/equipos`, label: "Mis equipos", icono: "equipos" },
    { href: `${D}/inscripciones`, label: "Inscripciones", icono: "inscripciones" },
    { href: `${D}/calendario`, label: "Calendario", icono: "calendario" },
    { href: `${D}/quejas`, label: "Quejas", icono: "quejas" },
    { href: `${D}/predicciones`, label: "Predicciones", icono: "predicciones" },
  ],
  JUGADOR: [
    { href: "/jugador", label: "Mi ficha", icono: "inicio", exacto: true },
    { href: "/campeonatos", label: "Campeonatos", icono: "campeonatos" },
  ],
};

export function itemActivo(item: ItemMenu, pathname: string): boolean {
  if (pathname === item.href) return true;
  return !item.exacto && pathname.startsWith(`${item.href}/`);
}

/** Rutas públicas (sin sesión): vista del ciudadano, calendario y resultados. */
export function esRutaPublica(pathname: string): boolean {
  return (
    pathname === "/" ||
    pathname === "/login" ||
    pathname === "/privacidad" || pathname === "/terminos" || pathname === "/cookies" ||            // documentos legales
    pathname === "/corporativo" || pathname.startsWith("/corporativo/") ||   // sitio corporativo y sus archivos (ficha PDF)
    pathname === "/campeonatos" || pathname.startsWith("/campeonatos/") ||
    pathname === "/partidos" || pathname.startsWith("/partidos/")
  );
}

const RUTAS_SOLO_ADMIN = ["/gestion/catalogos", "/gestion/usuarios", "/gestion/bitacora"];

/** Rol necesario para entrar a una ruta protegida; null si basta con tener sesión. */
export function rolesPermitidos(pathname: string): Rol[] | null {
  if (RUTAS_SOLO_ADMIN.some((r) => pathname === r || pathname.startsWith(`${r}/`))) return ROLES_ADMIN;
  if (pathname === "/gestion" || pathname.startsWith("/gestion/")) return ROLES_GESTION;
  if (pathname === "/planilla" || pathname.startsWith("/planilla/")) return ROLES_GESTION;     // F7-05: planilla móvil
  if (pathname === "/delegado" || pathname.startsWith("/delegado/")) return ["DELEGADO"];
  if (pathname === "/jugador" || pathname.startsWith("/jugador/")) return ["JUGADOR"];
  return null;
}

/** Destino tras el login: respeta `redirect` solo si el rol puede entrar allí. */
export function destinoTrasLogin(rol: Rol, redirect: string | null): string {
  if (redirect && redirect.startsWith("/") && !redirect.startsWith("//")) {
    const permitidos = rolesPermitidos(redirect);
    if (esRutaPublica(redirect) ? redirect !== "/login" : permitidos === null || permitidos.includes(rol)) return redirect;
  }
  return ROLE_HOME[rol];
}
