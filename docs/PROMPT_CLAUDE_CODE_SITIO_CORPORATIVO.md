# Prompt para Claude Code: implementar el sitio web corporativo (/corporativo)

Pega este archivo completo en Claude Code (VS Code) con la carpeta raíz DUBSS-GESTION-DEPORTIVA abierta. También puedes ponerlo en `docs/` y decirle: "Lee docs/PROMPT_CLAUDE_CODE_SITIO_CORPORATIVO.md y sigue sus fases".

---

Actúa como ingeniero frontend senior. Trabaja en `frontend/` (Next.js 14.2.5, React 18, TypeScript, Tailwind, lucide-react). Ya existe el sistema completo; solo vas a AGREGAR un sitio web corporativo público en `/corporativo`. Responde en español.

## Fase 1: analizar (NO modifiques nada todavía)
1. Lee: `frontend/components/layout/PublicShell.tsx`, `frontend/middleware.ts`, `frontend/lib/auth/roles.ts`, `frontend/tailwind.config.js`, `frontend/components/ui/*`, `frontend/components/layout/Logo.tsx`, `frontend/app/(publico)/page.tsx`, `frontend/app/layout.tsx` y `frontend/app/globals.css`.
2. Confirma o corrige estos supuestos sobre mi código: (a) `app/(publico)/` usa `PublicShell` como layout; (b) `esRutaPublica()` de `lib/auth/roles.ts` decide qué rutas no piden sesión; (c) existen `Card`, `Badge` y `Button` en `components/ui`; (d) `Logo` usa `/logo-dubss.png`; (e) la app no tiene modo oscuro; (f) `lucide-react` ya está instalado.
3. Dime en pocas líneas qué encontraste y si algo difiere. **Detente y espera mi "continúa"** antes de la Fase 2.

## Fase 2: implementar
Sigue las reglas y el orden de `docs/GUIA_SITIO_CORPORATIVO.md` (si no está, usa estas reglas):
- Ruta pública `/corporativo` dentro de `app/(publico)/`. No cambies `/`, `/login`, la API ni el panel.
- Cambios mínimos en archivos existentes: (1) `lib/auth/roles.ts`: agregar `pathname === "/corporativo"` en `esRutaPublica`; (2) `components/layout/PublicShell.tsx`: agregar `{ href: "/corporativo", label: "Producto" }` a `ENLACES` y un enlace "Sitio corporativo" en el pie.
- Todo lo editable (datos de la empresa y de la DUBSS) en `lib/corporativo.config.ts`; lo vacío se muestra como "Por confirmar". No inventes datos.
- Sin librerías nuevas. Sin `dangerouslySetInnerHTML`. Sin modo oscuro. Español, accesible y responsive hasta 400 px sin scroll horizontal.
- El formulario de contacto no envía nada: arma el mensaje y permite copiarlo o abrirlo con `mailto:` o `https://wa.me/` solo si están configurados.
- El chat es un asistente por reglas (sin IA ni servicios externos), rotulado "no es una persona".
- Datos de la DUBSS (reales, con autorización): Dirección Universitaria de Bienestar Social y Salud (D.U.B.S.S.), Av. Busch, Ciudad Universitaria (lado comedor universitario, Mod. 292), Santa Cruz de la Sierra; tel. 60040944; dubss@uagrm.edu.bo; oficinas 9:00 a 16:00; Facebook https://www.facebook.com/DireccionUniversitariaDeBienestarSocial; Instagram https://www.instagram.com/dubs_uagrm; TikTok https://www.tiktok.com/@dubs.oficial.uagrm; Linktree https://linktr.ee/dubssoficial. Aviso obligatorio: el sitio no es el oficial de la DUBSS ni de la UAGRM.

### Archivos a crear
Ya los probé sobre este mismo código; crea cada uno con el contenido del apéndice (puedes mejorar detalles si algo choca con tu análisis de la Fase 1, y avísame):
- `frontend/lib/corporativo.config.ts`
- `frontend/lib/corporativo.contenido.ts`
- `frontend/components/corporativo/CopiarBoton.tsx`
- `frontend/components/corporativo/ProductoModulos.tsx`
- `frontend/components/corporativo/SeccionDubss.tsx`
- `frontend/components/corporativo/Descargas.tsx`
- `frontend/components/corporativo/Soporte.tsx`
- `frontend/components/corporativo/Contacto.tsx`
- `frontend/components/corporativo/ChatAyuda.tsx`
- `frontend/components/corporativo/SitioCorporativo.tsx`
- `frontend/app/(publico)/corporativo/page.tsx`
- `frontend/public/corporativo/ficha-tecnica-sporttech-dubss.pdf` (cópialo desde `docs/` si lo puse allí; si no existe, deja el botón apuntando a esa ruta y avísame)

## Fase 3: verificar
- `cd frontend && npx tsc --noEmit` y `npm run lint` sin errores.
- Con `npm run dev`, abrir `/corporativo` sin sesión: carga sin ir al login. `/`, `/campeonatos`, `/login` igual que antes; `/gestion` sigue pidiendo sesión.
- Pestañas con flechas del teclado, botones Copiar, formulario (vacío da error; completo da el mensaje), chat con las 4 preguntas rápidas, y sin scroll horizontal a 400 px.
- Guarda capturas en `docs/capturas-sitio/` con los nombres: hero, producto, dubss, descargas, soporte, contacto, chat, movil.
- Termina con un resumen: archivos creados, archivos modificados (con el diff de los 2 existentes) y qué datos de `lib/corporativo.config.ts` quedan por completar (whatsapp, email, horarios, respuestas, appUrl, manualUrl, razón social).

---

## Apéndice: contenido de los archivos

### `frontend/lib/corporativo.config.ts`

```ts
/**
 * Datos del sitio web corporativo (/corporativo). Edita SOLO este archivo para completar
 * los datos de la empresa: lo que quede vacío se muestra como "Por confirmar".
 */
export const EMPRESA = {
  nombre: "SPORTECH-DUBSS S.R.L.", // denominación provisional: cambiar por la razón social definitiva
  producto: "SportTech DUBSS",
  ciudad: "Santa Cruz de la Sierra, Bolivia",
  whatsapp: "", // solo dígitos con código de país, ej.: 5917XXXXXXX
  email: "", // correo de contacto de la empresa
  horarioCorreo: "", // ej.: "Lunes a viernes, 08:00 a 18:00"
  horarioWhatsapp: "",
  respuestaCorreo: "", // ej.: "Máximo 8 horas hábiles"
  respuestaWhatsapp: "",
  appUrl: "", // dirección pública de la plataforma (cuando esté desplegada)
  manualUrl: "", // enlace al manual de usuario (PDF)
  fichaUrl: "/corporativo/ficha-tecnica-sporttech-dubss.pdf",
} as const;

/** Dirección usuaria. Datos públicos de la DUBSS, usados con su autorización para este proyecto. */
export const DUBSS = {
  nombre: "Dirección Universitaria de Bienestar Social y Salud",
  sigla: "D.U.B.S.S.",
  direccion: "Av. Busch, Ciudad Universitaria (lado comedor universitario, Mod. 292), Santa Cruz de la Sierra, Bolivia",
  telefono: "60040944",
  correo: "dubss@uagrm.edu.bo",
  horario: "9:00 a 16:00 (oficinas)",
  redes: [
    { etiqueta: "Facebook", href: "https://www.facebook.com/DireccionUniversitariaDeBienestarSocial" },
    { etiqueta: "Instagram", href: "https://www.instagram.com/dubs_uagrm" },
    { etiqueta: "TikTok", href: "https://www.tiktok.com/@dubs.oficial.uagrm" },
    { etiqueta: "Linktree", href: "https://linktr.ee/dubssoficial" },
  ],
} as const;

export const POR_CONFIRMAR = "Por confirmar";
```

### `frontend/lib/corporativo.contenido.ts`

```ts
/** Textos del sitio corporativo. Los equipos y cifras de las vistas de ejemplo son ficticios. */

export const MODULOS = [
  {
    id: "fixture", etiqueta: "Fixture automático",
    titulo: "Fixture que respeta canchas, horarios y clases",
    texto: "El organizador define el campeonato y el sistema propone el calendario completo. Un optimizador evita choques de cancha, descansos cortos y partidos en horarios de clases, y un modelo de aprendizaje automático asigna los mejores horarios según el clima.",
    puntos: ["Sin partidos superpuestos en la misma cancha", "Restricciones por horario de clases", "Riesgo climático con pronóstico de Open-Meteo", "Cambios con confirmación antes de publicarse"],
    pantalla: "Fixture · Jornada 4",
    cabecera: ["Hora", "Cancha", "Partido", "Clima"],
    filas: [["18:30", "1", "Ingeniería vs Medicina", "ok:Bajo"], ["19:30", "2", "Derecho vs Economía", "ok:Bajo"], ["20:30", "1", "Humanidades vs Tecnología", "wn:Medio"]],
    nota: "Vista de ejemplo con datos ficticios.",
  },
  {
    id: "posiciones", etiqueta: "Tabla de posiciones",
    titulo: "Posiciones que se actualizan al registrar el resultado",
    texto: "Cada resultado cargado recalcula la tabla con los criterios del reglamento del campeonato. También se guarda el historial de posiciones por jornada y se avisa de los resultados atípicos para que se revisen.",
    puntos: ["Puntos, diferencia de goles y desempates", "Historial por jornada", "Detección de resultados atípicos", "Consulta pública sin iniciar sesión"],
    pantalla: "Posiciones · Grupo A",
    cabecera: ["#", "Equipo", "PJ", "DG", "Pts"],
    filas: [["1", "Ingeniería", "4", "+6", "10"], ["2", "Derecho", "4", "+3", "8"], ["3", "Medicina", "4", "0", "5"], ["4", "Economía", "4", "-4", "3"]],
    nota: "Vista de ejemplo con datos ficticios.",
  },
  {
    id: "prediccion", etiqueta: "Predicción de resultados",
    titulo: "Probabilidades antes del partido",
    texto: "Un modelo Random Forest, combinado con un puntaje Elo de cada equipo, calcula la probabilidad de victoria, empate o derrota a partir del historial. Sirve para planificar y para animar el campeonato, no para decidir resultados.",
    puntos: ["Entrenamiento con el historial de partidos", "Reentrenamiento semanal automático", "Agrupamiento de equipos por nivel"],
    pantalla: "Predicción · Ingeniería vs Medicina",
    barras: [["Ingeniería", 52], ["Empate", 21], ["Medicina", 27]],
    nota: "Vista de ejemplo con datos ficticios.",
  },
  {
    id: "planilla", etiqueta: "Planilla sin conexión",
    titulo: "La planilla se llena aunque se corte el internet",
    texto: "El delegado registra goles, tarjetas y alineaciones en el celular. Si no hay conexión, los datos quedan guardados en el dispositivo y se envían solos al volver la señal, sin duplicarse. Además, un asistente por voz permite dictar el reporte del partido.",
    puntos: ["Aplicación web instalable (PWA)", "Envío seguro sin duplicados al reconectar", "Reportes por voz", "Notificaciones y recordatorios de partidos"],
    pantalla: "Planilla · Derecho vs Economía",
    cabecera: ["Min.", "Evento", "Jugador", "Estado"],
    filas: [["12'", "Gol", "J. Rojas", "ok:Enviado"], ["34'", "Tarjeta amarilla", "M. Vaca", "wn:En espera"], ["58'", "Gol", "L. Suárez", "wn:En espera"]],
    nota: "Sin conexión: 2 eventos se enviarán al reconectar. Datos ficticios.",
  },
] as const;

export const ROLES = [
  ["Superadministrador", "Configura el sistema, gestiona usuarios y roles y revisa la bitácora de auditoría."],
  ["Administrador DUBSS", "Administra facultades, deportes, instalaciones y supervisa los campeonatos."],
  ["Organizador", "Crea campeonatos, genera el fixture, registra resultados y resuelve quejas."],
  ["Delegado", "Inscribe a su equipo y jugadores, consulta sus partidos y llena la planilla."],
] as const;

export const NIVELES = [
  ["Nivel 1", "Asistente y preguntas frecuentes", "Respuestas inmediatas sobre el uso del sistema, la instalación y los roles."],
  ["Nivel 2", "Soporte funcional", "Atención por correo o WhatsApp para dudas de uso, cuentas y datos de un campeonato."],
  ["Nivel 3", "Ingeniería", "Fallas de la aplicación, la base de datos, el optimizador o los modelos de predicción. La infraestructura se coordina con el área de tecnología de la universidad cuando el sistema esté alojado allí."],
] as const;

export interface RespuestaAyuda { claves: string[]; texto: string; enlace?: { href: string; etiqueta: string } }

/** Base del asistente de ayuda: reglas por palabra clave, sin inteligencia artificial ni servicios externos. */
export const AYUDA: RespuestaAyuda[] = [
  { claves: ["ubicación", "ubicacion", "dónde", "donde", "sede", "teléfono", "telefono", "dirección de la dubss"], texto: "La DUBSS está en la Av. Busch, Ciudad Universitaria (lado comedor universitario, Mod. 292), Santa Cruz de la Sierra. Teléfono 60040944 y correo dubss@uagrm.edu.bo. Atiende en oficinas de 9:00 a 16:00.", enlace: { href: "#dubss", etiqueta: "Ver datos de la DUBSS" } },
  { claves: ["qué es", "que es", "sistema", "plataforma", "sporttech", "dubss", "para qué"], texto: "SportTech DUBSS es una plataforma web para organizar campeonatos deportivos universitarios: arma el fixture, calcula posiciones, predice resultados y permite llenar la planilla del partido sin conexión." },
  { claves: ["fixture", "calendario", "programar", "programación", "horario", "cancha"], texto: "El fixture se genera con un optimizador que evita choques de cancha, descansos cortos y horarios de clases, y usa un modelo de aprendizaje automático para elegir los mejores horarios. El organizador revisa y confirma antes de publicarlo." },
  { claves: ["predic", "probabilidad", "machine", "inteligencia", "ia", "modelo"], texto: "Un modelo Random Forest con puntaje Elo estima la probabilidad de victoria, empate o derrota de cada equipo. Se reentrena cada semana con el historial. Es una referencia, no decide resultados." },
  { claves: ["internet", "conexión", "conexion", "offline", "sin red", "planilla"], texto: "La planilla funciona sin internet: los eventos quedan guardados en el dispositivo y se envían solos, sin duplicarse, cuando vuelve la conexión." },
  { claves: ["voz", "dictar", "asistente"], texto: "El asistente por voz permite dictar el reporte de un partido. Toda acción que cambia datos pide confirmación antes de aplicarse." },
  { claves: ["rol", "usuario", "perfil", "permiso", "delegado", "organizador", "administrador"], texto: "Hay cuatro roles: Superadministrador, Administrador DUBSS, Organizador y Delegado. Cada uno ve solo las funciones que le corresponden." },
  { claves: ["instal", "app", "celular", "móvil", "movil", "pwa", "descargar"], texto: "Es una aplicación web instalable (PWA): se instala desde el navegador, sin tienda de aplicaciones. En Descargas está la ficha técnica en PDF.", enlace: { href: "#descargas", etiqueta: "Ir a Descargas" } },
  { claves: ["precio", "costo", "cuánto", "cuanto", "licencia", "cobr"], texto: "El precio y el modelo de licencia se acuerdan con cada institución. Escríbenos desde Contacto y te enviamos una propuesta.", enlace: { href: "#contacto", etiqueta: "Ir a Contacto" } },
  { claves: ["seguridad", "datos", "privacidad", "contraseña", "contrasena"], texto: "Las contraseñas se guardan con Argon2, la cuenta se bloquea 15 minutos tras 5 intentos fallidos, cada acción queda en una bitácora y cada usuario accede solo a lo que su rol permite." },
  { claves: ["soporte", "ayuda", "problema", "error", "falla"], texto: "Si el asistente no resuelve tu problema, escríbenos por correo o WhatsApp desde Contacto e indica qué estabas haciendo y qué mensaje apareció.", enlace: { href: "#soporte", etiqueta: "Ver niveles de soporte" } },
  { claves: ["contacto", "correo", "email", "whatsapp", "llamar", "hablar", "persona"], texto: "Puedes escribirnos por correo o WhatsApp desde la sección Contacto.", enlace: { href: "#contacto", etiqueta: "Ir a Contacto" } },
];
export const AYUDA_SIN_RESPUESTA: RespuestaAyuda = { claves: [], texto: "No tengo una respuesta para eso. Puedes escribirnos desde Contacto y una persona del equipo te responde.", enlace: { href: "#contacto", etiqueta: "Ir a Contacto" } };
export const PREGUNTAS_RAPIDAS = ["¿Qué es SportTech?", "¿Cómo funciona el fixture?", "¿Funciona sin internet?", "¿Cuánto cuesta?"];
```

### `frontend/components/corporativo/CopiarBoton.tsx`

```tsx
"use client";
import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { Button } from "@/components/ui";

/** Copia un texto al portapapeles; si el navegador lo impide, avisa para copiarlo a mano. */
export function CopiarBoton({ texto, etiqueta = "Copiar" }: { texto: string; etiqueta?: string }) {
  const [estado, setEstado] = useState<"idle" | "ok" | "error">("idle");
  async function copiar() {
    try {
      await navigator.clipboard.writeText(texto);
      setEstado("ok");
    } catch {
      setEstado("error");
    }
    setTimeout(() => setEstado("idle"), 1800);
  }
  return (
    <Button variant="secondary" size="sm" onClick={copiar} icon={estado === "ok" ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : <Copy className="h-3.5 w-3.5" aria-hidden="true" />}>
      {estado === "ok" ? "Copiado" : estado === "error" ? "Cópialo a mano" : etiqueta}
    </Button>
  );
}
```

### `frontend/components/corporativo/ProductoModulos.tsx`

```tsx
"use client";
import { useRef, useState, type KeyboardEvent } from "react";
import { cn } from "@/lib/utils";
import { MODULOS } from "@/lib/corporativo.contenido";

function Chip({ valor }: { valor: string }) {
  const [tono, texto] = valor.split(":");
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", tono === "ok" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800")}>{texto}</span>
  );
}

/** Pestañas accesibles (teclado: flechas izquierda/derecha) con vistas de ejemplo de cada módulo. */
export function ProductoModulos() {
  const [activo, setActivo] = useState(0);
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function teclas(e: KeyboardEvent, i: number) {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault();
    const n = (i + (e.key === "ArrowRight" ? 1 : MODULOS.length - 1)) % MODULOS.length;
    setActivo(n);
    refs.current[n]?.focus();
  }

  return (
    <div>
      <div role="tablist" aria-label="Módulos del producto" className="scroll-thin mb-5 flex gap-2 overflow-x-auto pb-1">
        {MODULOS.map((m, i) => (
          <button key={m.id} ref={(el) => { refs.current[i] = el; }} role="tab" type="button" id={`tab-${m.id}`} aria-selected={activo === i} aria-controls={`panel-${m.id}`}
            tabIndex={activo === i ? 0 : -1} onClick={() => setActivo(i)} onKeyDown={(e) => teclas(e, i)}
            className={cn("whitespace-nowrap rounded-full border px-4 py-2 text-sm font-medium transition-colors",
              activo === i ? "border-brand-600 bg-brand-600 text-white" : "border-ink-200 bg-white text-ink-700 hover:bg-ink-50")}>
            {m.etiqueta}
          </button>
        ))}
      </div>

      {MODULOS.map((m, i) => (
        <div key={m.id} role="tabpanel" id={`panel-${m.id}`} aria-labelledby={`tab-${m.id}`} hidden={activo !== i}
          className="grid min-w-0 gap-6 rounded-xl border border-ink-200 bg-white p-5 shadow-card md:grid-cols-2 md:p-6">
          <div className="min-w-0">
            <h3 className="text-lg font-semibold text-ink-900">{m.titulo}</h3>
            <p className="mt-2 text-sm leading-relaxed text-ink-600">{m.texto}</p>
            <ul className="mt-4 space-y-1.5 text-sm text-ink-700">
              {m.puntos.map((p) => (
                <li key={p} className="flex gap-2"><span aria-hidden="true" className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-600" />{p}</li>
              ))}
            </ul>
          </div>
          <div className="min-w-0 overflow-hidden rounded-lg border border-ink-200 bg-ink-50">
            <div className="flex items-center gap-1.5 border-b border-ink-200 bg-white px-3 py-2">
              <span className="h-2.5 w-2.5 rounded-full bg-ink-200" /><span className="h-2.5 w-2.5 rounded-full bg-ink-200" /><span className="h-2.5 w-2.5 rounded-full bg-ink-200" />
              <span className="ml-2 truncate text-xs font-medium text-ink-600">{m.pantalla}</span>
            </div>
            <div className="p-3">
              {"filas" in m ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead><tr className="text-ink-500">{m.cabecera.map((c) => <th key={c} scope="col" className="px-2 py-1.5 font-medium">{c}</th>)}</tr></thead>
                    <tbody>
                      {m.filas.map((f, r) => (
                        <tr key={r} className="border-t border-ink-200 text-ink-800">
                          {f.map((c, k) => <td key={k} className="px-2 py-2">{/^(ok|wn):/.test(c) ? <Chip valor={c} /> : c}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="space-y-3 py-1">
                  {m.barras.map(([nombre, pct], k) => (
                    <div key={nombre} className="grid grid-cols-[5.5rem_1fr_2.5rem] items-center gap-2 text-xs text-ink-700">
                      <span className="truncate">{nombre}</span>
                      <div className="h-2.5 overflow-hidden rounded-full bg-ink-200" role="img" aria-label={`${nombre}: ${pct} por ciento`}>
                        <div className={cn("h-full rounded-full", k === 1 ? "bg-ink-400" : "bg-brand-600")} style={{ width: `${pct}%` }} />
                      </div>
                      <b className="text-right">{pct}%</b>
                    </div>
                  ))}
                </div>
              )}
              <p className="mt-3 text-[11px] text-ink-500">{m.nota}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
```

### `frontend/components/corporativo/SeccionDubss.tsx`

```tsx
import { Clock, Mail, MapPin, Phone } from "lucide-react";
import { Logo } from "@/components/layout/Logo";
import { DUBSS } from "@/lib/corporativo.config";
import { CopiarBoton } from "./CopiarBoton";

function Fila({ icono, etiqueta, children, accion }: { icono: React.ReactNode; etiqueta: string; children: React.ReactNode; accion?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-ink-200 border-l-4 border-l-[#03662C] bg-white px-4 py-3">
      <div className="flex min-w-0 items-start gap-3">
        <span className="mt-0.5 text-[#03662C]" aria-hidden="true">{icono}</span>
        <div className="min-w-0">
          <span className="block text-xs font-medium uppercase tracking-wide text-ink-500">{etiqueta}</span>
          <span className="block break-words text-sm font-medium text-ink-900">{children}</span>
        </div>
      </div>
      {accion}
    </div>
  );
}

/** Dirección usuaria: datos públicos de la DUBSS, con su autorización para este proyecto. */
export function SeccionDubss() {
  return (
    <div className="grid gap-8 md:grid-cols-[18rem_1fr] md:items-start">
      <div className="flex flex-col items-center gap-3 text-center">
        <Logo size={200} className="shadow-pop ring-8 ring-brand-100" />
        <p className="text-sm font-semibold text-ink-900">{DUBSS.sigla} · UAGRM</p>
      </div>
      <div className="min-w-0 space-y-3">
        <Fila icono={<MapPin className="h-4 w-4" />} etiqueta="Dirección">{DUBSS.direccion}</Fila>
        <Fila icono={<Phone className="h-4 w-4" />} etiqueta="Teléfono" accion={<CopiarBoton texto={DUBSS.telefono} />}>{DUBSS.telefono}</Fila>
        <Fila icono={<Mail className="h-4 w-4" />} etiqueta="Correo" accion={<CopiarBoton texto={DUBSS.correo} />}>{DUBSS.correo}</Fila>
        <Fila icono={<Clock className="h-4 w-4" />} etiqueta="Horario de atención">{DUBSS.horario}</Fila>
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="mr-1 text-xs font-medium uppercase tracking-wide text-ink-500">Redes de la DUBSS</span>
          {DUBSS.redes.map((r) => (
            <a key={r.etiqueta} href={r.href} target="_blank" rel="noopener noreferrer"
              className="inline-flex h-8 items-center rounded-lg border border-ink-200 bg-white px-3 text-xs font-medium text-ink-800 transition-colors hover:bg-ink-50">
              {r.etiqueta}
            </a>
          ))}
        </div>
        <p className="text-xs text-ink-500">
          Datos y escudo usados con autorización de la DUBSS para este proyecto. Este sitio lo mantiene el proveedor del sistema y no es el sitio oficial de la DUBSS ni de la UAGRM.
        </p>
      </div>
    </div>
  );
}
```

### `frontend/components/corporativo/Descargas.tsx`

```tsx
import { Download, ExternalLink, FileText, Smartphone } from "lucide-react";
import { Badge, Card } from "@/components/ui";
import { EMPRESA } from "@/lib/corporativo.config";

function Accion({ href, children, primario }: { href: string; children: React.ReactNode; primario?: boolean }) {
  const clases = "inline-flex h-10 items-center justify-center gap-2 rounded-lg px-4 text-sm font-medium transition-colors";
  if (!href) return <span aria-disabled="true" className={`${clases} cursor-not-allowed border border-ink-200 bg-ink-100 text-ink-500`}>{children}</span>;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
      className={`${clases} ${primario ? "bg-brand-600 text-white hover:bg-brand-700" : "border border-ink-200 bg-white text-ink-800 hover:bg-ink-50"}`}>
      {children}
    </a>
  );
}

export function Descargas() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card className="flex flex-col gap-3 p-5">
        <FileText className="h-6 w-6 text-brand-600" aria-hidden="true" />
        <h3 className="font-semibold text-ink-900">Ficha técnica</h3>
        <p className="flex-1 text-sm text-ink-600">Resumen de funciones, tecnologías, requisitos y seguridad del sistema.</p>
        <Badge tono="neutral">PDF · 2 páginas</Badge>
        <Accion href={EMPRESA.fichaUrl} primario><Download className="h-4 w-4" aria-hidden="true" />Abrir la ficha (PDF)</Accion>
      </Card>
      <Card className="flex flex-col gap-3 p-5">
        <FileText className="h-6 w-6 text-brand-600" aria-hidden="true" />
        <h3 className="font-semibold text-ink-900">Manual de usuario</h3>
        <p className="flex-1 text-sm text-ink-600">Guía paso a paso por rol: Superadministrador, Administrador, Organizador y Delegado.</p>
        {!EMPRESA.manualUrl && <Badge tono="warning">Manual por publicar</Badge>}
        <Accion href={EMPRESA.manualUrl}><Download className="h-4 w-4" aria-hidden="true" />Descargar manual</Accion>
      </Card>
      <Card className="flex flex-col gap-3 p-5">
        <Smartphone className="h-6 w-6 text-brand-600" aria-hidden="true" />
        <h3 className="font-semibold text-ink-900">Aplicación web (PWA)</h3>
        <p className="flex-1 text-sm text-ink-600">Se instala desde el navegador del celular o la computadora, sin tienda de aplicaciones.</p>
        <Badge tono="success">Instalable desde el navegador</Badge>
        <Accion href={EMPRESA.appUrl || "/login"} primario><ExternalLink className="h-4 w-4" aria-hidden="true" />Abrir la plataforma</Accion>
      </Card>
    </div>
  );
}
```

### `frontend/components/corporativo/Soporte.tsx`

```tsx
import { EMPRESA, POR_CONFIRMAR } from "@/lib/corporativo.config";
import { NIVELES } from "@/lib/corporativo.contenido";
import { Card } from "@/components/ui";

const o = (v: string) => v || POR_CONFIRMAR;

export function Soporte() {
  const canales = [
    ["Asistente de ayuda", "Preguntas frecuentes sobre el producto", "Siempre", "Inmediata"],
    ["Correo electrónico", "Consultas, solicitudes y reportes de errores", o(EMPRESA.horarioCorreo), o(EMPRESA.respuestaCorreo)],
    ["WhatsApp", "Atención rápida durante los campeonatos", o(EMPRESA.horarioWhatsapp), o(EMPRESA.respuestaWhatsapp)],
  ];
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        {NIVELES.map(([nivel, titulo, texto]) => (
          <Card key={nivel} className="p-5">
            <span className="text-xs font-semibold uppercase tracking-wider text-brand-700">{nivel}</span>
            <h3 className="mt-1 font-semibold text-ink-900">{titulo}</h3>
            <p className="mt-2 text-sm text-ink-600">{texto}</p>
          </Card>
        ))}
      </div>
      <Card className="overflow-x-auto">
        <table className="w-full min-w-[34rem] text-left text-sm">
          <caption className="sr-only">Canales de soporte, disponibilidad y tiempo de respuesta</caption>
          <thead className="bg-ink-50 text-xs uppercase tracking-wide text-ink-500">
            <tr>{["Canal", "Para qué sirve", "Disponibilidad", "Respuesta"].map((c) => <th key={c} scope="col" className="px-4 py-3 font-medium">{c}</th>)}</tr>
          </thead>
          <tbody>
            {canales.map((f) => (
              <tr key={f[0]} className="border-t border-ink-100">
                <th scope="row" className="px-4 py-3 font-medium text-ink-900">{f[0]}</th>
                <td className="px-4 py-3 text-ink-600">{f[1]}</td>
                <td className={`px-4 py-3 ${f[2] === POR_CONFIRMAR ? "text-ink-400" : "text-ink-700"}`}>{f[2]}</td>
                <td className={`px-4 py-3 ${f[3] === POR_CONFIRMAR ? "text-ink-400" : "text-ink-700"}`}>{f[3]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
```

### `frontend/components/corporativo/Contacto.tsx`

```tsx
"use client";
import { useState, type FormEvent } from "react";
import { Mail, MessageCircle } from "lucide-react";
import { Button } from "@/components/ui";
import { EMPRESA, POR_CONFIRMAR } from "@/lib/corporativo.config";
import { CopiarBoton } from "./CopiarBoton";

const MOTIVOS = ["Quiero una demostración", "Consulta sobre el producto", "Necesito soporte técnico", "Otro"];
const campo = "mt-1 w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 placeholder:text-ink-400";

/**
 * El formulario NO envía nada por sí mismo: arma el mensaje y ofrece abrirlo en el correo o en
 * WhatsApp (si están configurados en corporativo.config.ts) o copiarlo.
 */
export function Contacto({ onAbrirChat }: { onAbrirChat: () => void }) {
  const [nombre, setNombre] = useState("");
  const [org, setOrg] = useState("");
  const [motivo, setMotivo] = useState(MOTIVOS[0]);
  const [mensaje, setMensaje] = useState("");
  const [listo, setListo] = useState<string | null>(null);
  const [error, setError] = useState("");

  function preparar(e: FormEvent) {
    e.preventDefault();
    if (!nombre.trim() || !mensaje.trim()) { setError("Escribe tu nombre y tu mensaje."); setListo(null); return; }
    setError("");
    setListo(`Hola, soy ${nombre.trim()}${org.trim() ? ` (${org.trim()})` : ""}.\nMotivo: ${motivo}.\n\n${mensaje.trim()}`);
  }

  const urlCorreo = EMPRESA.email && listo ? `mailto:${EMPRESA.email}?subject=${encodeURIComponent(`${EMPRESA.producto}: ${motivo}`)}&body=${encodeURIComponent(listo)}` : "";
  const urlWa = EMPRESA.whatsapp && listo ? `https://wa.me/${EMPRESA.whatsapp}?text=${encodeURIComponent(listo)}` : "";

  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <div className="min-w-0 space-y-3">
        <div className="rounded-lg border border-ink-200 bg-white px-4 py-3">
          <span className="block text-xs font-medium uppercase tracking-wide text-ink-500">Correo</span>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="break-all text-sm font-medium text-ink-900">{EMPRESA.email || POR_CONFIRMAR}</span>
            {EMPRESA.email && <CopiarBoton texto={EMPRESA.email} />}
          </div>
        </div>
        <div className="rounded-lg border border-ink-200 bg-white px-4 py-3">
          <span className="block text-xs font-medium uppercase tracking-wide text-ink-500">WhatsApp</span>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-sm font-medium text-ink-900">{EMPRESA.whatsapp ? `+${EMPRESA.whatsapp}` : POR_CONFIRMAR}</span>
            {EMPRESA.whatsapp && <CopiarBoton texto={`+${EMPRESA.whatsapp}`} />}
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-ink-200 bg-white px-4 py-3">
          <div>
            <span className="block text-xs font-medium uppercase tracking-wide text-ink-500">Chat de ayuda</span>
            <span className="text-sm font-medium text-ink-900">Asistente en esta página</span>
          </div>
          <Button variant="secondary" size="sm" onClick={onAbrirChat}>Abrir chat</Button>
        </div>
      </div>

      <form onSubmit={preparar} noValidate className="min-w-0 space-y-3 rounded-xl border border-ink-200 bg-white p-5 shadow-card">
        <label className="block text-sm font-medium text-ink-800" htmlFor="c-nombre">Nombre
          <input id="c-nombre" className={campo} value={nombre} onChange={(e) => setNombre(e.target.value)} autoComplete="name" placeholder="Tu nombre" aria-invalid={!!error && !nombre.trim()} />
        </label>
        <label className="block text-sm font-medium text-ink-800" htmlFor="c-org">Facultad o institución
          <input id="c-org" className={campo} value={org} onChange={(e) => setOrg(e.target.value)} placeholder="Ej.: Facultad de Ingeniería" />
        </label>
        <label className="block text-sm font-medium text-ink-800" htmlFor="c-motivo">Motivo
          <select id="c-motivo" className={campo} value={motivo} onChange={(e) => setMotivo(e.target.value)}>
            {MOTIVOS.map((m) => <option key={m}>{m}</option>)}
          </select>
        </label>
        <label className="block text-sm font-medium text-ink-800" htmlFor="c-mensaje">Mensaje
          <textarea id="c-mensaje" className={`${campo} min-h-[7rem]`} value={mensaje} onChange={(e) => setMensaje(e.target.value)} placeholder="Cuéntanos qué necesitas" aria-invalid={!!error && !mensaje.trim()} />
        </label>
        <Button type="submit">Preparar mensaje</Button>
        {error && <p role="alert" className="text-sm font-medium text-brand-700">{error}</p>}
        {listo && (
          <div role="status" className="space-y-3 rounded-lg border border-ink-200 bg-ink-50 p-3">
            <p className="text-sm font-medium text-ink-800">Mensaje listo. Este formulario no lo envía por sí mismo: cópialo o ábrelo en tu correo o WhatsApp.</p>
            <pre className="whitespace-pre-wrap break-words rounded-md bg-white p-3 text-xs text-ink-700">{listo}</pre>
            <div className="flex flex-wrap gap-2">
              <CopiarBoton texto={listo} etiqueta="Copiar mensaje" />
              {urlCorreo && <a href={urlCorreo} className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-ink-200 bg-white px-3 text-xs font-medium text-ink-800 hover:bg-ink-50"><Mail className="h-3.5 w-3.5" aria-hidden="true" />Abrir en correo</a>}
              {urlWa && <a href={urlWa} target="_blank" rel="noopener noreferrer" className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-ink-200 bg-white px-3 text-xs font-medium text-ink-800 hover:bg-ink-50"><MessageCircle className="h-3.5 w-3.5" aria-hidden="true" />Abrir en WhatsApp</a>}
            </div>
            {!urlCorreo && !urlWa && <p className="text-xs text-ink-500">El correo y el WhatsApp de la empresa aún no están configurados ({POR_CONFIRMAR}); por ahora solo puedes copiar el mensaje.</p>}
          </div>
        )}
      </form>
    </div>
  );
}
```

### `frontend/components/corporativo/ChatAyuda.tsx`

```tsx
"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Bot, Send, X } from "lucide-react";
import { AYUDA, AYUDA_SIN_RESPUESTA, PREGUNTAS_RAPIDAS, type RespuestaAyuda } from "@/lib/corporativo.contenido";

type Mensaje = { de: "yo" | "bot"; texto: string; enlace?: RespuestaAyuda["enlace"] };

function responder(pregunta: string): RespuestaAyuda {
  const s = pregunta.toLowerCase();
  return AYUDA.find((r) => r.claves.some((k) => s.includes(k))) ?? AYUDA_SIN_RESPUESTA;
}

/** Asistente de preguntas frecuentes por reglas (no es una persona ni usa IA ni servicios externos). */
export function ChatAyuda({ abierto, setAbierto }: { abierto: boolean; setAbierto: (v: boolean) => void }) {
  const [mensajes, setMensajes] = useState<Mensaje[]>([{ de: "bot", texto: "Hola. Soy un asistente automático con respuestas sobre el producto. ¿En qué te ayudo?" }]);
  const [texto, setTexto] = useState("");
  const fin = useRef<HTMLDivElement>(null);
  const entrada = useRef<HTMLInputElement>(null);

  useEffect(() => { fin.current?.scrollIntoView({ block: "end" }); }, [mensajes]);
  useEffect(() => { if (abierto) entrada.current?.focus(); }, [abierto]);

  function preguntar(p: string) {
    const r = responder(p);
    setMensajes((m) => [...m, { de: "yo", texto: p }, { de: "bot", texto: r.texto, enlace: r.enlace }]);
  }
  function enviar(e: FormEvent) {
    e.preventDefault();
    const p = texto.trim();
    if (!p) return;
    setTexto("");
    preguntar(p);
  }

  return (
    <>
      <button type="button" aria-expanded={abierto} aria-controls="chat-ayuda" onClick={() => setAbierto(!abierto)}
        className="fixed bottom-4 right-4 z-40 inline-flex h-12 items-center gap-2 rounded-full bg-brand-600 px-5 text-sm font-semibold text-white shadow-pop transition-colors hover:bg-brand-700">
        <Bot className="h-5 w-5" aria-hidden="true" />Chat de ayuda
      </button>
      {abierto && (
        <aside id="chat-ayuda" aria-label="Chat de ayuda"
          className="fixed bottom-20 right-4 z-40 flex max-h-[min(32rem,calc(100vh-7rem))] w-[min(22rem,calc(100vw-2rem))] flex-col overflow-hidden rounded-xl border border-ink-200 bg-white shadow-pop animate-slide-up">
          <header className="flex items-start justify-between gap-2 bg-ink-900 px-4 py-3 text-white">
            <div><b className="block text-sm">Asistente SportTech</b><small className="text-xs text-ink-300">Respuestas automáticas · no es una persona</small></div>
            <button type="button" onClick={() => setAbierto(false)} aria-label="Cerrar chat" className="rounded p-1 text-ink-200 hover:bg-white/10"><X className="h-4 w-4" /></button>
          </header>
          <div className="scroll-thin flex-1 space-y-2 overflow-y-auto bg-ink-50 p-3" aria-live="polite">
            {mensajes.map((m, i) => (
              <div key={i} className={m.de === "yo" ? "ml-auto max-w-[85%] rounded-xl rounded-br-sm bg-brand-600 px-3 py-2 text-sm text-white" : "mr-auto max-w-[90%] rounded-xl rounded-bl-sm border border-ink-200 bg-white px-3 py-2 text-sm text-ink-800"}>
                {m.texto}
                {m.enlace && <a href={m.enlace.href} onClick={() => setAbierto(false)} className="mt-1 block font-medium text-brand-700 underline">{m.enlace.etiqueta}</a>}
              </div>
            ))}
            <div ref={fin} />
          </div>
          <div className="flex flex-wrap gap-1.5 border-t border-ink-100 bg-white px-3 py-2">
            {PREGUNTAS_RAPIDAS.map((q) => (
              <button key={q} type="button" onClick={() => preguntar(q)} className="rounded-full border border-ink-200 px-2.5 py-1 text-xs text-ink-700 hover:bg-ink-50">{q}</button>
            ))}
          </div>
          <form onSubmit={enviar} className="flex gap-2 border-t border-ink-100 bg-white p-3">
            <input ref={entrada} value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Escribe tu pregunta" autoComplete="off" aria-label="Tu pregunta"
              className="min-w-0 flex-1 rounded-lg border border-ink-200 px-3 text-sm" />
            <button type="submit" className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-brand-600 px-3 text-sm font-medium text-white hover:bg-brand-700"><Send className="h-4 w-4" aria-hidden="true" /><span className="sr-only">Enviar</span></button>
          </form>
        </aside>
      )}
    </>
  );
}
```

### `frontend/components/corporativo/SitioCorporativo.tsx`

```tsx
"use client";
import { useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Logo } from "@/components/layout/Logo";
import { Card } from "@/components/ui";
import { DUBSS, EMPRESA } from "@/lib/corporativo.config";
import { ROLES } from "@/lib/corporativo.contenido";
import { ChatAyuda } from "./ChatAyuda";
import { Contacto } from "./Contacto";
import { Descargas } from "./Descargas";
import { ProductoModulos } from "./ProductoModulos";
import { SeccionDubss } from "./SeccionDubss";
import { Soporte } from "./Soporte";

const ANCLAS = [["producto", "Producto"], ["dubss", "La DUBSS"], ["descargas", "Descargas"], ["soporte", "Soporte"], ["contacto", "Contacto"]];

function Seccion({ id, etiqueta, titulo, texto, children }: { id: string; etiqueta: string; titulo: string; texto?: string; children: React.ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-t`} className="scroll-mt-32 py-10">
      <span className="text-xs font-semibold uppercase tracking-wider text-brand-700">{etiqueta}</span>
      <h2 id={`${id}-t`} className="mt-1 max-w-3xl text-2xl font-bold tracking-tight text-ink-900 sm:text-3xl [text-wrap:balance]">{titulo}</h2>
      {texto && <p className="mt-3 max-w-3xl text-ink-600">{texto}</p>}
      <div className="mt-6">{children}</div>
    </section>
  );
}

export function SitioCorporativo() {
  const [chat, setChat] = useState(false);
  return (
    <>
      <section className="overflow-hidden rounded-2xl bg-gradient-to-br from-brand-700 via-brand-800 to-brand-900 px-6 py-10 text-white shadow-pop sm:px-10 sm:py-14">
        <div className="flex flex-col items-center gap-8 text-center md:flex-row md:text-left">
          <div className="max-w-2xl">
            <span className="text-xs font-semibold uppercase tracking-wider text-brand-200">{EMPRESA.producto}</span>
            <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl [text-wrap:balance]">Gestión deportiva universitaria, de la cancha a la tabla</h1>
            <p className="mt-3 text-brand-100">
              Plataforma web para organizar campeonatos, programar partidos con optimización, registrar resultados sin conexión y consultar estadísticas. Desarrollada para la {DUBSS.nombre} (DUBSS) de la UAGRM.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-3 md:justify-start">
              <a href="#producto" className="inline-flex h-11 items-center gap-2 rounded-lg bg-white px-5 text-sm font-semibold text-brand-800 transition-colors hover:bg-brand-50">Ver producto <ArrowRight className="h-4 w-4" aria-hidden="true" /></a>
              <a href="#descargas" className="inline-flex h-11 items-center rounded-lg border border-white/40 px-5 text-sm font-medium text-white transition-colors hover:bg-white/10">Descargar información</a>
            </div>
            <ul className="mt-6 flex flex-wrap justify-center gap-2 text-xs md:justify-start">
              {["4 roles de usuario", "Fixture con optimización", "Planilla sin conexión"].map((p) => <li key={p} className="rounded-full bg-white/10 px-3 py-1">{p}</li>)}
            </ul>
          </div>
          <Logo size={160} className="shrink-0 shadow-pop ring-8 ring-white/15 md:ml-auto" />
        </div>
      </section>

      <nav aria-label="Secciones de esta página" className="scroll-thin sticky top-16 z-20 -mx-4 mt-4 flex gap-2 overflow-x-auto border-b border-ink-200 bg-ink-50/95 px-4 py-2 backdrop-blur sm:-mx-6 sm:px-6">
        {ANCLAS.map(([id, t]) => (
          <a key={id} href={`#${id}`} className="whitespace-nowrap rounded-full px-3 py-1.5 text-sm font-medium text-ink-700 hover:bg-white hover:text-brand-700">{t}</a>
        ))}
      </nav>

      <Seccion id="quienes" etiqueta="Quiénes somos" titulo="Un equipo de ingeniería que entiende cómo se organiza un campeonato universitario"
        texto={`${EMPRESA.producto} desarrolla software para la gestión deportiva. El sistema nació como proyecto de la asignatura Ingeniería de Software II de la Facultad de Ingeniería en Ciencias de la Computación y Telecomunicaciones (FICCT) de la UAGRM, y está pensado para la DUBSS. Nuestro propósito es que la programación, el registro de resultados y la comunicación con los equipos sean transparentes, rápidos y auditables.`}>
        <div className="grid gap-4 md:grid-cols-3">
          {[["Misión", "Menos horas en hojas de cálculo", "Reemplazar la programación manual de partidos y los conteos en papel por un proceso automático y verificable."],
            ["Visión", "Estándar para el deporte universitario", "Ser la plataforma que usan las facultades para organizar sus torneos de forma justa y con datos confiables."],
            ["Principios", "Transparencia, seguridad, disponibilidad", "Todo cambio queda registrado, cada usuario ve solo lo que le corresponde y la planilla funciona aun sin conexión."]].map(([t, h, p]) => (
            <Card key={t} className="p-5"><span className="text-xs font-semibold uppercase tracking-wider text-brand-700">{t}</span><h3 className="mt-1 font-semibold text-ink-900">{h}</h3><p className="mt-2 text-sm text-ink-600">{p}</p></Card>
          ))}
        </div>
      </Seccion>

      <Seccion id="producto" etiqueta="Producto" titulo="Lo que hace el sistema, con vistas de ejemplo"
        texto="Elige un módulo para ver cómo se presenta la información. Los equipos y las cifras de estas vistas son ficticios. Para ver el sistema con datos propios, ingresa con tu cuenta.">
        <ProductoModulos />
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {ROLES.map(([t, p]) => <Card key={t} className="p-5"><h3 className="font-semibold text-ink-900">{t}</h3><p className="mt-2 text-sm text-ink-600">{p}</p></Card>)}
        </div>
        <p className="mt-4 text-sm text-ink-600">¿Ya tienes cuenta? <Link href="/login" className="font-medium text-brand-700 underline">Ingresar al sistema</Link> · <Link href="/campeonatos" className="font-medium text-brand-700 underline">Ver campeonatos y resultados públicos</Link></p>
      </Seccion>

      <Seccion id="dubss" etiqueta="Dirección usuaria" titulo="Desarrollado para la DUBSS de la UAGRM"
        texto="La Dirección Universitaria de Bienestar Social y Salud es la unidad de la UAGRM que planifica y coordina las actividades deportivas de la comunidad universitaria, entre ellas los torneos interfacultativos. El sistema se construye para su trabajo diario.">
        <SeccionDubss />
      </Seccion>

      <Seccion id="descargas" etiqueta="Descargas" titulo="Lleva la información del producto contigo" texto="Documentos para evaluar el sistema y acceso a la aplicación.">
        <Descargas />
      </Seccion>

      <Seccion id="soporte" etiqueta="Soporte técnico" titulo="Tres niveles de atención, del autoservicio al ingeniero"
        texto="Puedes resolver las dudas frecuentes con el asistente de la esquina inferior derecha. Si no alcanza, el caso sube de nivel.">
        <Soporte />
      </Seccion>

      <Seccion id="contacto" etiqueta="Contacto" titulo="Hablemos de tu campeonato" texto="Escríbenos por el canal que prefieras. Responderemos con el detalle del sistema y una demostración.">
        <Contacto onAbrirChat={() => setChat(true)} />
      </Seccion>

      <p className="border-t border-ink-200 pt-4 text-xs text-ink-500">
        {EMPRESA.nombre} (denominación provisional) · {EMPRESA.ciudad}. Proyecto desarrollado en la FICCT, UAGRM, para la DUBSS. Esta página no es un sitio oficial de la universidad ni de la DUBSS.
      </p>
      <ChatAyuda abierto={chat} setAbierto={setChat} />
    </>
  );
}
```

### `frontend/app/(publico)/corporativo/page.tsx`

```tsx
import type { Metadata } from "next";
import { SitioCorporativo } from "@/components/corporativo/SitioCorporativo";

export const metadata: Metadata = {
  title: "SportTech DUBSS — Sitio corporativo",
  description: "Plataforma de gestión deportiva universitaria desarrollada para la Dirección Universitaria de Bienestar Social y Salud (UAGRM).",
};

export default function PaginaCorporativa() {
  return <SitioCorporativo />;
}
```
