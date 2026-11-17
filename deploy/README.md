# Despliegue de la DUBSS en producción

Guía paso a paso para poner el sistema en internet, **desde cero y sin experiencia previa en la nube**. Todo corre en **un solo servidor** (una máquina virtual) con Docker: es lo más simple, lo más barato y alcanza de sobra para una universidad.

```
Internet ──► Caddy (HTTPS automático) ──► Next.js (la aplicación web) ──► Django (API, interna)
                                                                         ├─► PostgreSQL  (datos)
                                                                         ├─► Redis + Celery (tareas en segundo plano)
                                                                         └─► n8n (WhatsApp, opcional)
```

* **Lo único expuesto a internet** es Caddy (puertos 80 y 443). La base de datos, Redis, el backend y n8n no son accesibles desde fuera.
* **La API de Django no es pública**: solo la aplicación web habla con ella. Por eso los scripts, Swagger y la interfaz de DRF no son un riesgo.
* Los **respaldos diarios** de la base de datos y de las fotos se hacen solos.

---

## Antes de empezar: qué necesitas

| Qué | Para qué | Costo aproximado |
|---|---|---|
| Una **cuenta en una nube** (AWS, Azure o Google Cloud) | El servidor | Ver el paso 1 |
| Una **tarjeta de débito/crédito con compras por internet** (Visa/Mastercard) | Todas las nubes la piden para verificar la cuenta (Azure for Students puede no pedirla) | — |
| Un **dominio** (ej.: `dubss.uagrm.edu.bo`) | El HTTPS, la app instalable y las cookies seguras lo exigen | Gratis (subdominio) o ~US$12 al año |
| Una **cuenta de correo** para enviar avisos (Gmail sirve) | Recordatorios y avisos | Gratis |
| Clave de **Groq** (opcional) | Asistente y agente de IA | Gratis |

> **Consejo:** pregunta al área de tecnología de la UAGRM si pueden darte un subdominio como `dubss.uagrm.edu.bo`. Solo tienen que crear un registro DNS apuntando a la IP de tu servidor. Es lo más profesional y gratis.

---

## Paso 1 — Elegir la nube y crear la cuenta

El servidor necesita **2 CPU y 4 GB de memoria** (el sistema completo usa ≈1,4 GB en reposo medidos; el resto es margen para el optimizador y el entrenamiento de IA). Elige región **São Paulo** (la más cercana a Bolivia).

### Opción A (recomendada): AWS Lightsail
La más simple: precio fijo por mes, IP fija y firewall en un solo panel.

1. Entra a <https://aws.amazon.com> → **Crear una cuenta de AWS**. Pide correo, contraseña, nombre, teléfono y tarjeta. Elige el plan de soporte **Basic (gratis)**.
2. Las cuentas nuevas reciben **créditos de bienvenida** (a la fecha de esta guía, del orden de US$100 a 200, con vigencia de varios meses; **confirma las condiciones vigentes** en <https://aws.amazon.com/free/>). El plan gratuito se cierra solo si se acaban los créditos, así que no hay cobros sorpresa.
3. **Activa la verificación en dos pasos** en tu cuenta (Seguridad → MFA) y crea una **alerta de presupuesto** (servicio *Budgets*, por ejemplo US$30 al mes).
4. Abre <https://lightsail.aws.amazon.com> y arriba a la derecha cambia la región a **São Paulo (sa-east-1)**.
5. **Crear instancia** → plataforma **Linux/Unix** → *Solo sistema operativo* → **Ubuntu 24.04 LTS**.
6. Plan: **4 GB de memoria, 2 vCPU, 80 GB SSD** (≈ US$24 al mes). Ponle el nombre `dubss` y créala.
7. Pestaña **Redes**:
   * **Crear IP estática** y asóciala a la instancia (así la IP no cambia si reinicias).
   * En **Firewall IPv4** agrega las reglas **HTTPS (TCP 443)** y **Personalizada UDP 443**. Deben quedar abiertos 22, 80 y 443.
8. Anota la **IP estática**: la necesitas para el dominio.
9. (Recomendado) Pestaña **Instantáneas** → activa los **instantáneas automáticas** (copia de todo el servidor; cuesta unos US$1 al mes).

### Opción B (sin tarjeta, si eres estudiante): Azure for Students
Con un correo universitario (`@uagrm.edu.bo`) ofrece **US$100 por un año** sin tarjeta (según [Microsoft](https://learn.microsoft.com/en-us/azure/education-hub/faq); se verifica automáticamente la institución).

1. <https://azure.microsoft.com/free/students> → *Empezar* → verifica con tu correo universitario.
2. Portal de Azure → **Máquinas virtuales** → Crear → región **Brazil South**, imagen **Ubuntu Server 24.04 LTS**, tamaño **Standard_B2s** (2 vCPU, 4 GB; ≈ US$30 al mes: el crédito rinde unos 3 meses).
3. Autenticación con **clave SSH** (descarga el `.pem`). En *Redes* abre los puertos **22, 80 y 443**.
4. Anota la **IP pública** y, en la IP, marca **Asignación: estática**.

### Opción C: Google Cloud
**US$300 por 90 días** (pide tarjeta; [condiciones](https://docs.cloud.google.com/free)). Compute Engine → región `southamerica-east1` → máquina `e2-medium` → Ubuntu 24.04 → permitir HTTP y HTTPS.

---

## Paso 2 — El dominio

El dominio debe apuntar a la **IP del servidor** con un registro **A**.

| Si tienes… | Haz esto |
|---|---|
| Un subdominio de la UAGRM | Pide al área de TI: *registro A* `dubss` → tu IP |
| Un dominio comprado (Namecheap, Porkbun, Cloudflare…) | En su panel DNS: registro **A**, nombre `@` (o `dubss`), valor = tu IP |
| Nada todavía (solo una demostración) | Crea un subdominio gratis en <https://www.duckdns.org> (ej. `dubss-uagrm.duckdns.org`) y pon tu IP |

Comprueba que ya apunta bien (puede tardar de minutos a unas horas): en tu PC, `nslookup dubss.uagrm.edu.bo` debe mostrar tu IP. **Sin esto Caddy no puede emitir el certificado HTTPS.**

---

## Paso 3 — Preparar el servidor (una sola vez)

1. **Conéctate por SSH**: en Lightsail, botón *Conectarse mediante SSH* (se abre en el navegador). En Azure/Google, con tu clave: `ssh -i clave.pem azureuser@TU_IP`.
2. Descarga el proyecto. Como tu repositorio es **privado**, crea un *token* de solo lectura: GitHub → Settings → Developer settings → *Personal access tokens* → **Fine-grained** → solo el repositorio `DUBSS-GESTION-DEPORTIVA`, permiso **Contents: Read-only**.
   ```bash
   sudo apt-get update && sudo apt-get install -y git
   git clone https://TU_USUARIO:TU_TOKEN@github.com/TU_USUARIO/DUBSS-GESTION-DEPORTIVA.git
   cd DUBSS-GESTION-DEPORTIVA
   ```
3. Instala Docker, el firewall, las actualizaciones automáticas, la zona horaria y la memoria de respaldo:
   ```bash
   bash deploy/scripts/instalar-servidor.sh
   ```
4. **Cierra la sesión y vuelve a entrar** (para usar Docker sin `sudo`).

---

## Paso 4 — Configurar (`.env`)

```bash
cd DUBSS-GESTION-DEPORTIVA/deploy
./scripts/generar-env.sh
```
Pregunta tu dominio (ej. `dubss.uagrm.edu.bo`) y si quieres WhatsApp. Crea `deploy/.env` con **contraseñas y claves aleatorias** y una **ruta secreta para el panel de administración**.

Luego edita lo que falta:
```bash
nano .env        # Ctrl+O para guardar, Ctrl+X para salir
```
* `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD`: tu correo. Con Gmail necesitas una **contraseña de aplicación** (Cuenta de Google → Seguridad → Verificación en 2 pasos → Contraseñas de aplicaciones).
* `GROQ_API_KEY`: opcional (<https://console.groq.com>).

> ⚠️ **Guarda una copia del `.env` en un gestor de contraseñas o un lugar seguro.** Contiene las claves del sistema; sin ellas no se puede restaurar. **Nunca lo subas a Git.**

---

## Paso 5 — Desplegar

```bash
./scripts/desplegar.sh
```
La primera vez construye las imágenes (**5 a 10 minutos**), arranca todo, migra la base y espera a que el sistema esté sano. Al terminar muestra la dirección. Caddy pide solo el certificado HTTPS a Let's Encrypt (si falla, revisa el paso 2 y que el puerto 80/443 estén abiertos).

## Paso 6 — Primer inicio (sin datos de ejemplo)

```bash
./scripts/primer-inicio.sh
```
* Carga los **catálogos base**: las 12 facultades de la UAGRM, los deportes (Fútbol, Futsal, Voleibol, Baloncesto) y sus categorías.
* Crea tu **primer superadministrador** (te pide correo, nombre, apellido y contraseña).

**No** se cargan equipos, partidos ni usuarios de ejemplo: el sistema arranca limpio, listo para datos reales.

Entra a `https://TU_DOMINIO/login` y:
1. Crea las **instalaciones y canchas** (Catálogos).
2. Crea las cuentas de **organizadores** y **delegados** (Usuarios). Cada persona acepta los términos en su primer ingreso.
3. Revisa los **textos legales** (`/privacidad`, `/terminos`, `/cookies`) con la Asesoría Jurídica de la UAGRM y ajusta el correo del responsable si hace falta (`frontend/lib/legal.config.ts`).

Los modelos de IA (predicción, niveles de equipos) se entrenan solos cada domingo en la madrugada cuando haya partidos jugados; también puedes entrenarlos desde el panel (*Inteligencia artificial*).

---

## Día a día

| Tarea | Comando (dentro de `deploy/`) |
|---|---|
| Ver el estado, memoria, disco y último respaldo | `./scripts/estado.sh` |
| Ver los registros de un servicio | `docker compose logs --tail 100 -f backend` |
| **Actualizar** a la última versión | `./scripts/desplegar.sh` |
| Reiniciar un servicio | `docker compose restart backend` |
| Respaldo inmediato | `./scripts/respaldar-ahora.sh` |
| Restaurar un respaldo | `./scripts/restaurar.sh` (lista) y `./scripts/restaurar.sh bd-AAAAMMDD-HHMMSS.dump` |
| Detener todo | `docker compose down` (los datos **no** se borran) |

### Respaldos
* **Automáticos**: todos los días a las 03:15 (hora de Bolivia) se guarda la base de datos y las fotos en el servidor; se conservan 14 días.
* **Un respaldo en el mismo servidor no basta** (si el servidor se pierde, se pierde también). Descarga uno a tu computadora cada semana: `./scripts/respaldar-ahora.sh --copiar` y luego, desde tu PC, `scp usuario@IP:/tmp/bd-*.dump .`. Además activa las **instantáneas automáticas** del proveedor (Lightsail/Azure/Google).
* **Prueba restaurar** al menos una vez antes de depender de los respaldos.

### Monitoreo
Pon un monitor gratuito (p. ej. <https://uptimerobot.com>) que consulte `https://TU_DOMINIO/api/health` cada 5 minutos: te avisa por correo si el sistema cae.

### Acceso al panel de Django
La ruta está en tu `.env` (`ADMIN_URL`): `https://TU_DOMINIO/panel-xxxxxxxx/`. Solo entran cuentas con rol de administrador. La documentación de la API (Swagger) está **apagada**; para activarla temporalmente, `API_DOCS_ENABLED=true` en el `.env` y `docker compose up -d`.

---

## Opcionales

### Notificaciones push (app Android)
1. Crea un proyecto en <https://console.firebase.google.com> → *Cuentas de servicio* → **Generar nueva clave privada**.
2. Copia ese JSON al servidor como `deploy/secrets/firebase.json` y reinicia: `docker compose up -d`.
3. Compila el APK con la dirección de tu dominio (instrucciones en el repositorio `DUBSS-DOCS-MOVIL`, `mobile/`).

### Avisos por WhatsApp (n8n)
1. En el `.env`, `N8N_SECRETO` y `N8N_ENCRYPTION_KEY` con valores aleatorios (`openssl rand -hex 32`) y `N8N_URL_EVENTOS=http://n8n:5678/webhook/dubss-eventos`. (Si respondiste «sí» en el paso 4, ya están.)
2. Credenciales de Meta (WhatsApp Cloud API): `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_VERIFY_TOKEN`.
3. `./scripts/desplegar.sh` (detecta n8n y lo levanta). El webhook público queda en `https://TU_DOMINIO/webhook/whatsapp`; el **editor de n8n nunca se expone** (para abrirlo: `ssh -L 5678:localhost:5678 usuario@IP` y entra a <http://localhost:5678>).
4. Detalle de la plantilla de Meta y el flujo: guía de integración en el repositorio `DUBSS-DOCS-MOVIL` (`docs/INTEGRACION_N8N_WHATSAPP.md`).

---

## Seguridad: lista de comprobación

- [ ] Verificación en dos pasos en la cuenta de la nube y en GitHub.
- [ ] Alerta de presupuesto creada.
- [ ] `.env` guardado fuera del servidor y **no** en Git.
- [ ] Solo los puertos 22, 80 y 443 abiertos (`sudo ufw status`).
- [ ] Acceso SSH solo con clave (el valor por defecto en las nubes).
- [ ] Respaldo descargado a tu PC y restauración probada.
- [ ] Monitor de disponibilidad activo.
- [ ] Textos legales revisados por el área jurídica.
- [ ] Cambia la contraseña del superadministrador en *Mi perfil* y no la compartas.

## Si algo falla

| Síntoma | Causa probable y solución |
|---|---|
| El navegador dice «no seguro» / no hay certificado | El dominio no apunta a la IP (paso 2) o el puerto 80/443 está cerrado. Revisa con `docker compose logs caddy`. |
| `desplegar.sh` dice que el backend no quedó sano | `docker compose logs --tail 80 backend`. Suele ser una variable del `.env` mal escrita o la base aún iniciando: reintenta. |
| No puedo iniciar sesión (vuelve al login) | Estás entrando por `http://` en un servidor con `USAR_HTTPS=true`. Usa siempre `https://`. |
| El servidor va lento o se reinicia solo | Falta de memoria: `./scripts/estado.sh`. Verifica que el servidor tenga 4 GB y que el swap esté activo (`free -h`). |
| «No space left on device» | `docker system prune -f` (no borra los datos) y revisa `./scripts/estado.sh`. |
| No llegan los correos | Revisa `EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` (contraseña de aplicación de Gmail) y `docker compose logs backend`. |
| Olvidé la contraseña del superadministrador | `docker compose exec backend python manage.py changepassword correo@uagrm.edu.bo` |

## Costos (referencia, a la fecha de esta guía)

| Concepto | Costo |
|---|---|
| Servidor 4 GB (Lightsail) | ≈ US$24 al mes (cubierto por los créditos iniciales los primeros meses) |
| Instantáneas automáticas | ≈ US$1 al mes |
| Dominio `.com` | ≈ US$12 al año (o gratis con un subdominio institucional/DuckDNS) |
| Certificado HTTPS | Gratis (Let's Encrypt) |
| Correo, Groq, Firebase | Gratis en el uso de este sistema |
