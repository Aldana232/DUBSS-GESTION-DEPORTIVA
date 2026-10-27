# Prompt maestro para Copilot (uno por tarea)

Cómo usarlo: abre un chat NUEVO de Copilot en modo Agente, adjunta `docs/PLAN_FASES_DUBSS.md` y `docs/ANEXO_PLAN_FASES.md`, cambia `<ID>` por la tarea (por ejemplo `F0-05b`) y pega el bloque. Una tarea por chat. Cuando termine, revisa el reporte y avanza a la siguiente tarea en el orden del plan.

---

```
Lee docs/PLAN_FASES_DUBSS.md, docs/ANEXO_PLAN_FASES.md y .github/copilot-instructions.md.
Ejecuta SOLO la tarea <ID>. Si el anexo la modifica o la divide, manda el anexo sobre el plan.

REGLAS (obligatorias)
- NO ejecutes git commit, git push ni git add. Deja los cambios sin commitear.
- No borres la base de datos ni datos. Las migraciones NUEVAS están permitidas cuando la tarea las necesita;
  nunca modifiques migraciones ya existentes.
- No toques archivos que la tarea no necesite. Si crees que hace falta, dilo en el reporte.
- Todo mensaje que vea el usuario va en español, sin mezclar inglés (incluidos los de DRF).
- Nunca guardes contraseñas, tokens ni secretos en logs, bitácora ni respuestas.
- La seguridad real vive en la API: no confíes en el frontend ni en claims del JWT para autorizar.

MÉTODO
1. ANTES de editar, lee el código real relacionado con la tarea. El plan describe el estado por inspección:
   si algo no coincide con lo que ves, repórtalo.
2. Si una instrucción choca con la realidad o con otra regla (por ejemplo, una versión que no resuelve el
   problema), DETENTE y explícalo en vez de improvisar. No hagas cambios parciales que no cumplan el objetivo.
3. Si la tarea hace una migración de datos, muestra primero cuántas filas hay afectadas.
4. Implementa y escribe tests nuevos para cada comportamiento (casos felices, de error y de permisos).
5. Ejecuta SIEMPRE la suite completa: docker compose -f docker-compose.dev.yml exec backend pytest -q
   (y pytest dos veces si agregaste tests con caché, throttle o tiempo).
   Ejecuta también: python -m pyflakes <apps tocadas>, python manage.py makemigrations --check y git status --short.
   Si ya había hallazgos de pyflakes antes de tu cambio, sepáralos de los que introdujiste.
6. Frontend (cuando aplique): npm run lint && npm run build; no dejes errores nuevos.
7. No marques la tarea como terminada si falla algún test.

REPORTE FINAL (exactamente este formato)
1) Archivos creados/modificados y qué cambió (1 línea por archivo); nombres de migraciones.
2) Tests nuevos (nombres).
3) Resultado de pytest (suite completa), pyflakes, makemigrations --check y git status --short.
4) Discrepancias entre el plan y el código real que encontraste.
5) Cualquier cambio fuera de lo pedido y cualquier duda.
```

---

## Cuándo detenerte y pedir revisión humana

Revisa tú el diff (o pásalo a Claude) en estas tareas, porque un error aquí es caro o silencioso:

| Tarea | Por qué |
|---|---|
| F0-06, F0-07 | Seguridad de sesión y contraseñas |
| F1-01 a F1-06 | Migraciones de datos y cambio del modelo (roles, facultad, equipo/inscripción) |
| F1-11 | Constraint de exclusión en PostgreSQL |
| F2-01, F2-02, F2-07 | Permisos por rol y por facultad |
| F3-03, F3-05, F3-06 | Fixture, resultados y tabla: lógica deportiva central |
| F4-05 | Sesión con cookies httpOnly |
| F6-01, F6-06, F7-01 | ML, reportes por voz y agente |

En el resto, basta con que el reporte indique tests en verde y que el `git status` solo muestre lo esperado.
