"""
apps/fixture/services/tabla.py
RF13 — Tabla de posiciones recalculable e historial por jornada.

La tabla es una desnormalización controlada: siempre se reconstruye desde los
`Resultado`, de modo que registrar, corregir o borrar un resultado produce la
misma tabla que calcular desde cero.

Criterios de desempate (en orden): puntos, diferencia de goles, goles a favor,
enfrentamiento directo entre los equipos empatados (puntos, diferencia y goles
en los partidos entre ellos) y, por último, el nombre del equipo.
"""
from collections import defaultdict

from django.db import transaction

from apps.deportes.models import Campeonato, Inscripcion
from apps.fixture.models import Partido, PosicionHistorial, TablaPosiciones

ESTADOS_JUGADOS = (Partido.Estado.FINALIZADO, Partido.Estado.WALKOVER)


def _puntos(campeonato, favor, contra):
    if favor > contra:
        return campeonato.puntos_victoria
    if favor == contra:
        return campeonato.puntos_empate
    return campeonato.puntos_derrota


def _fila_vacia(equipo):
    return {"equipo": equipo, "pj": 0, "pg": 0, "pe": 0, "pp": 0,
            "gf": 0, "gc": 0, "puntos": 0}


def _acumular(fila, campeonato, favor, contra):
    fila["pj"] += 1
    fila["gf"] += favor
    fila["gc"] += contra
    fila["puntos"] += _puntos(campeonato, favor, contra)
    if favor > contra:
        fila["pg"] += 1
    elif favor == contra:
        fila["pe"] += 1
    else:
        fila["pp"] += 1


def _desempatar_enfrentamiento_directo(campeonato, grupo, partidos):
    """Ordena un grupo de filas empatadas por su mini-liga de enfrentamientos directos."""
    ids = {f["equipo"].pk for f in grupo}
    mini = {pk: _fila_vacia(None) for pk in ids}
    for p in partidos:
        if p.equipo_local_id in ids and p.equipo_visitante_id in ids:
            r = p.resultado
            _acumular(mini[p.equipo_local_id], campeonato, r.goles_local, r.goles_visitante)
            _acumular(mini[p.equipo_visitante_id], campeonato, r.goles_visitante, r.goles_local)

    def clave(fila):
        m = mini[fila["equipo"].pk]
        return (-m["puntos"], -(m["gf"] - m["gc"]), -m["gf"], fila["equipo"].nombre.lower())

    return sorted(grupo, key=clave)


def calcular_posiciones(campeonato: Campeonato, hasta_jornada: int | None = None) -> list[dict]:
    """Devuelve las filas de la tabla ordenadas, cada una con su `posicion`."""
    partidos = list(
        Partido.objects.filter(
            campeonato=campeonato,
            estado__in=ESTADOS_JUGADOS,
            resultado__isnull=False,
            equipo_local__isnull=False,
            equipo_visitante__isnull=False,
        ).select_related("resultado", "equipo_local", "equipo_visitante")
    )
    if hasta_jornada is not None:
        partidos = [p for p in partidos if p.jornada <= hasta_jornada]

    filas: dict[int, dict] = {}
    for inscripcion in Inscripcion.objects.filter(
        campeonato=campeonato, estado=Inscripcion.Estado.APROBADA
    ).select_related("equipo"):
        filas[inscripcion.equipo_id] = _fila_vacia(inscripcion.equipo)

    for p in partidos:
        for equipo in (p.equipo_local, p.equipo_visitante):
            filas.setdefault(equipo.pk, _fila_vacia(equipo))
        r = p.resultado
        _acumular(filas[p.equipo_local_id], campeonato, r.goles_local, r.goles_visitante)
        _acumular(filas[p.equipo_visitante_id], campeonato, r.goles_visitante, r.goles_local)

    base = sorted(
        filas.values(),
        key=lambda f: (-f["puntos"], -(f["gf"] - f["gc"]), -f["gf"]),
    )

    ordenadas: list[dict] = []
    i = 0
    while i < len(base):
        j = i
        clave = (base[i]["puntos"], base[i]["gf"] - base[i]["gc"], base[i]["gf"])
        while j < len(base) and (
            base[j]["puntos"], base[j]["gf"] - base[j]["gc"], base[j]["gf"]
        ) == clave:
            j += 1
        grupo = base[i:j]
        if len(grupo) > 1:
            grupo = _desempatar_enfrentamiento_directo(campeonato, grupo, partidos)
        ordenadas.extend(grupo)
        i = j

    for posicion, fila in enumerate(ordenadas, start=1):
        fila["posicion"] = posicion
    return ordenadas


@transaction.atomic
def recalcular(campeonato: Campeonato) -> list[TablaPosiciones]:
    """Reconstruye por completo la tabla del campeonato (idempotente)."""
    filas = calcular_posiciones(campeonato)
    equipos_ids = {f["equipo"].pk for f in filas}
    TablaPosiciones.objects.filter(campeonato=campeonato).exclude(
        equipo_id__in=equipos_ids
    ).delete()
    existentes = {
        t.equipo_id: t for t in TablaPosiciones.objects.filter(campeonato=campeonato)
    }
    resultado = []
    for fila in filas:
        tabla = existentes.get(fila["equipo"].pk) or TablaPosiciones(
            campeonato=campeonato, equipo=fila["equipo"]
        )
        for campo in ("pj", "pg", "pe", "pp", "gf", "gc", "puntos", "posicion"):
            setattr(tabla, campo, fila[campo])
        tabla.save()
        resultado.append(tabla)
    actualizar_historial(campeonato)
    return resultado


def jornadas_cerradas(campeonato: Campeonato) -> list[int]:
    """Jornadas cuyos partidos terminaron todos (FINALIZADO o WALKOVER)."""
    totales: dict[int, int] = defaultdict(int)
    jugados: dict[int, int] = defaultdict(int)
    for jornada, estado in Partido.objects.filter(campeonato=campeonato).values_list(
        "jornada", "estado"
    ):
        totales[jornada] += 1
        if estado in ESTADOS_JUGADOS:
            jugados[jornada] += 1
    return sorted(j for j, total in totales.items() if jugados[j] == total)


@transaction.atomic
def actualizar_historial(campeonato: Campeonato) -> None:
    """Reconstruye la foto de posiciones de cada jornada cerrada (idempotente)."""
    PosicionHistorial.objects.filter(campeonato=campeonato).delete()
    nuevas = []
    for jornada in jornadas_cerradas(campeonato):
        for fila in calcular_posiciones(campeonato, hasta_jornada=jornada):
            nuevas.append(PosicionHistorial(
                campeonato=campeonato,
                jornada=jornada,
                equipo=fila["equipo"],
                posicion=fila["posicion"],
                puntos=fila["puntos"],
                pj=fila["pj"],
                gf=fila["gf"],
                gc=fila["gc"],
            ))
    PosicionHistorial.objects.bulk_create(nuevas)


def historial_por_jornada(campeonato: Campeonato) -> list[dict]:
    """Evolución de posiciones agrupada por jornada, lista para serializar."""
    filas = PosicionHistorial.objects.filter(campeonato=campeonato).select_related("equipo")
    por_jornada: dict[int, list[dict]] = defaultdict(list)
    for h in filas:
        por_jornada[h.jornada].append({
            "equipo": h.equipo_id,
            "equipo_nombre": h.equipo.nombre,
            "posicion": h.posicion,
            "puntos": h.puntos,
            "pj": h.pj,
            "gf": h.gf,
            "gc": h.gc,
        })
    return [
        {"jornada": jornada, "posiciones": sorted(items, key=lambda i: i["posicion"])}
        for jornada, items in sorted(por_jornada.items())
    ]
