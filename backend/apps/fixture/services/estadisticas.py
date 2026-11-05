"""
apps/fixture/services/estadisticas.py
RF19 — Estadísticas públicas de un campeonato (goleadores, tarjetas, resumen).
Solo expone nombres y totales: nunca carnet ni datos personales.
"""
from django.db.models import Count, Q

from apps.deportes.models import Campeonato
from apps.fixture.models import Incidencia, Partido, Resultado, TablaPosiciones

LIMITE_RANKING = 10


def _nombre(ficha) -> str:
    return f"{ficha.nombre} {ficha.apellido}".strip()


def estadisticas_campeonato(campeonato: Campeonato) -> dict:
    partidos = Partido.objects.filter(campeonato=campeonato)
    resultados = Resultado.objects.filter(partido__campeonato=campeonato)

    jugados = resultados.count()
    goles = sum(r.goles_local + r.goles_visitante for r in resultados)
    local = sum(1 for r in resultados if r.goles_local > r.goles_visitante)
    visitante = sum(1 for r in resultados if r.goles_visitante > r.goles_local)

    incidencias = (
        Incidencia.objects.filter(partido__campeonato=campeonato, jugador__isnull=False)
        .values("jugador", "jugador__nombre", "jugador__apellido", "jugador__equipo__nombre")
        .annotate(
            goles=Count("id", filter=Q(tipo=Incidencia.Tipo.GOL)),
            amarillas=Count("id", filter=Q(tipo=Incidencia.Tipo.TARJETA_AMARILLA)),
            rojas=Count("id", filter=Q(tipo=Incidencia.Tipo.TARJETA_ROJA)),
        )
    )

    def fila(i):
        return {
            "jugador_id": i["jugador"],
            "jugador": f"{i['jugador__nombre']} {i['jugador__apellido']}".strip(),
            "equipo": i["jugador__equipo__nombre"],
        }

    goleadores = sorted(
        (i for i in incidencias if i["goles"] > 0),
        key=lambda i: (-i["goles"], i["jugador__apellido"]),
    )[:LIMITE_RANKING]
    tarjetas = sorted(
        (i for i in incidencias if i["amarillas"] or i["rojas"]),
        key=lambda i: (-i["rojas"], -i["amarillas"], i["jugador__apellido"]),
    )[:LIMITE_RANKING]

    tabla = list(TablaPosiciones.objects.filter(campeonato=campeonato, pj__gt=0).select_related("equipo"))
    mejor_ataque = max(tabla, key=lambda t: t.gf, default=None)
    mejor_defensa = min(tabla, key=lambda t: t.gc, default=None)

    return {
        "resumen": {
            "partidos_total": partidos.count(),
            "partidos_jugados": jugados,
            "goles": goles,
            "promedio_goles": round(goles / jugados, 2) if jugados else 0,
            "victorias_local": local,
            "empates": jugados - local - visitante,
            "victorias_visitante": visitante,
        },
        "goleadores": [{**fila(i), "goles": i["goles"]} for i in goleadores],
        "tarjetas": [
            {**fila(i), "amarillas": i["amarillas"], "rojas": i["rojas"]} for i in tarjetas
        ],
        "mejor_ataque": {"equipo": mejor_ataque.equipo.nombre, "goles": mejor_ataque.gf} if mejor_ataque else None,
        "mejor_defensa": {"equipo": mejor_defensa.equipo.nombre, "goles": mejor_defensa.gc} if mejor_defensa else None,
    }
