# Guía: cómo adaptar e implementar el sitio web corporativo en DUBSS-GESTION-DEPORTIVA

Esta guía fija el orden y las reglas. El prompt para Claude Code (`PROMPT_CLAUDE_CODE_SITIO_CORPORATIVO.md`) la usa como base. Ya se probó esta solución sobre tu código (Next.js 14.2.5, Tailwind, rutas públicas, PublicShell): `tsc` y `next lint` sin errores y sin desborde horizontal a 400 px.

## 1. Qué se construye
Una página pública en `/corporativo`, del proveedor del sistema (SportTech DUBSS), con: inicio, quiénes somos, producto (pestañas con vistas de ejemplo), roles, La DUBSS (datos reales y escudo), descargas, soporte en 3 niveles, contacto (formulario) y un chat de ayuda por reglas.

## 2. Cómo es tu código hoy (lo que condiciona la solución)
- `app/(publico)/` ya agrupa las rutas sin sesión y usa `PublicShell` (cabecera oscura, menú Inicio / Campeonatos / Ingresar y pie).
- `middleware.ts` deja pasar solo lo que `esRutaPublica()` (en `lib/auth/roles.ts`) declara público; todo lo demás exige sesión.
- Tailwind con `brand` (rojo #d21115) e `ink` (neutros), fuente Inter, componentes en `components/ui` (Card, Badge, Button…) y escudo en `components/layout/Logo.tsx`.
- La app solo tiene tema claro (no hay modo oscuro).

## 3. Decisiones
1. Ruta `/corporativo` dentro de `app/(publico)/` (hereda cabecera y pie). `/` sigue siendo el inicio de campeonatos y `/login` no cambia.
2. Todos los datos editables viven en un solo archivo: `lib/corporativo.config.ts`. Lo vacío se muestra como "Por confirmar"; no se inventa nada.
3. Los textos (módulos, roles, niveles de soporte, preguntas del asistente) viven en `lib/corporativo.contenido.ts`.
4. Sin librerías nuevas: solo React, Tailwind y `lucide-react`, que ya están instalados.
5. Sin modo oscuro, para ser coherente con el resto de la app.

## 4. Orden de trabajo
1. **Analizar sin tocar nada.** Leer `PublicShell.tsx`, `middleware.ts`, `lib/auth/roles.ts`, `tailwind.config.js`, `components/ui/*`, `Logo.tsx` y `app/(publico)/page.tsx`. Confirmar que lo de la sección 2 sigue siendo cierto en tu copia actual.
2. **Crear la configuración y el contenido** (`lib/corporativo.config.ts`, `lib/corporativo.contenido.ts`).
3. **Crear los componentes** en `components/corporativo/`: `CopiarBoton`, `ProductoModulos`, `SeccionDubss`, `Descargas`, `Soporte`, `Contacto`, `ChatAyuda`, `SitioCorporativo`.
4. **Crear la página** `app/(publico)/corporativo/page.tsx` (componente de servidor con `metadata`).
5. **Copiar la ficha técnica** a `public/corporativo/ficha-tecnica-sporttech-dubss.pdf`.
6. **Hacer los 2 cambios mínimos en archivos existentes:**
   - `lib/auth/roles.ts`: en `esRutaPublica`, agregar `pathname === "/corporativo"`.
   - `components/layout/PublicShell.tsx`: agregar `{ href: "/corporativo", label: "Producto" }` a `ENLACES` y el enlace "Sitio corporativo" en el pie.
7. **Verificar** (sección 6) y mostrarme el resumen de archivos creados y modificados.

## 5. Reglas
- Español en todo el texto visible; accesibilidad: foco visible, `aria-*` en pestañas y chat, contraste suficiente, enlace "saltar al contenido" (ya lo da PublicShell).
- Responsive hasta 400 px sin scroll horizontal.
- No tocar el login, la API, el middleware (salvo lo de `roles.ts`), ni el panel.
- No usar `dangerouslySetInnerHTML`; los enlaces de las respuestas del chat son datos (`{href, etiqueta}`).
- El formulario de contacto NO envía nada: arma el mensaje y ofrece copiarlo o abrirlo con `mailto:` / `https://wa.me/` solo si el correo y el WhatsApp están configurados.
- El chat es un asistente por reglas, rotulado "no es una persona"; no usar IA ni servicios externos.
- Las vistas de ejemplo del producto son datos ficticios y lo dicen. Las capturas reales del sistema se agregan después en `public/corporativo/`.
- Datos de la DUBSS (reales, usados con su autorización): nombre, dirección, teléfono 60040944, correo dubss@uagrm.edu.bo, horario de oficinas 9:00 a 16:00, Facebook, Instagram, TikTok y Linktree. Mostrar siempre el aviso de que el sitio no es el oficial de la DUBSS ni de la UAGRM.
- Colores: solo `brand` e `ink` de tu Tailwind; el verde #03662C del escudo únicamente como acento en la sección de la DUBSS.

## 6. Verificación
- `cd frontend && npx tsc --noEmit` y `npm run lint` sin errores.
- `npm run dev` y abrir `/corporativo` sin sesión (debe cargar, sin redirigir al login).
- `/`, `/campeonatos` y `/login` siguen igual; una ruta protegida (`/gestion`) sigue pidiendo sesión.
- Pestañas con teclado (flechas), copiar teléfono y correo, formulario (vacío → error; completo → mensaje listo), chat con las 4 preguntas rápidas.
- A 400 px: sin scroll horizontal.
- Guardar capturas en `docs/capturas-sitio/` con estos nombres: `hero`, `producto`, `dubss`, `descargas`, `soporte`, `contacto`, `chat`, `movil`.

## 7. Qué completar después
En `lib/corporativo.config.ts`: `whatsapp`, `email`, `horarioCorreo`, `horarioWhatsapp`, `respuestaCorreo`, `respuestaWhatsapp`, `appUrl`, `manualUrl` y la razón social definitiva (`nombre`).
