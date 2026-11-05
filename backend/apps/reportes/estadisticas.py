"""
apps/reportes/estadisticas.py
RF16 / F6-05 — Estadísticas deportivas por jugador, equipo y facultad (y torneo, ver fixture.services.estadisticas).

Reglas: solo cuentan partidos FINALIZADOS con marcador real (los W.O. son decisiones administrativas,
no rendimiento). Todas las funciones devuelven datos simples y serializables.
"""
from __future__ import annotations

from collections import defaultdict

from django.db.models import Count, Q

from apps.deportes.models import Equipo, Facultad, FichaJugador
from apps.fixture.models import Incidencia, Partido

T = Incidencia.Tipo


def _jugados(filtro: Q):
    return (
        Partido.objects.filter(filtro, estado=Partido.Estado.FINALIZADO, resultado__isnull=False, resultado__walkover=False)
        .select_related("resultado", "campeonato")
    )


def rendimiento_de_equipo(equipo_id: int) -> dict:
    """PJ, PG, PE, PP, GF, GC, DG y puntos (3-1-0) de un equipo en TODOS sus campeonatos."""
    r = {"pj": 0, "pg": 0, "pe": 0, "pp": 0, "gf": 0, "gc": 0}
    campeonatos = set()
    for p in _jugados(Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)):
        gf, gc = ((p.resultado.goles_local, p.resultado.goles_visitante) if p.equipo_local_id == equipo_id
                  else (p.resultado.goles_visitante, p.resultado.goles_local))
        r["pj"] += 1
        r["gf"] += gf
        r["gc"] += gc
        r["pg" if gf > gc else "pe" if gf == gc else "pp"] += 1
        campeonatos.add(p.campeonato.nombre)
    r["dg"] = r["gf"] - r["gc"]
    r["puntos"] = 3 * r["pg"] + r["pe"]
    r["campeonatos"] = sorted(campeonatos)
    return r


def _incidencias_por_jugador(filtro: Q) -> dict:
    filas = (
        Incidencia.objects.filter(filtro, jugador__isnull=False)
        .values("jugador").annotate(
            goles=Count("id", filter=Q(tipo=T.GOL)),
            amarillas=Count("id", filter=Q(tipo=T.TARJETA_AMARILLA)),
            rojas=Count("id", filter=Q(tipo=T.TARJETA_ROJA)),
        )
    )
    return {f["jugador"]: f for f in filas}


def estadisticas_equipo(equipo: Equipo) -> dict:
    por_jugador = _incidencias_por_jugador(Q(jugador__equipo=equipo))
    plantel = []
    for j in FichaJugador.objects.filter(equipo=equipo, estado="ACTIVO").order_by("numero_camiseta", "apellido"):
        i = por_jugador.get(j.pk, {})
        plantel.append({"jugador": f"{j.nombre} {j.apellido}", "numero": j.numero_camiseta,
                        "goles": i.get("goles", 0), "amarillas": i.get("amarillas", 0), "rojas": i.get("rojas", 0),
                        "sancion": j.partidos_sancion_restantes})
    return {"equipo": equipo.nombre, "facultad": equipo.facultad.nombre, **rendimiento_de_equipo(equipo.pk),
            "plantel": plantel}


def estadisticas_jugador(jugador: FichaJugador) -> dict:
    i = _incidencias_por_jugador(Q(jugador=jugador)).get(jugador.pk, {})
    return {"jugador": f"{jugador.nombre} {jugador.apellido}", "equipo": jugador.equipo.nombre,
            "facultad": jugador.equipo.facultad.nombre, "posicion": jugador.posicion, "numero": jugador.numero_camiseta,
            "goles": i.get("goles", 0), "amarillas": i.get("amarillas", 0), "rojas": i.get("rojas", 0),
            "sancion_pendiente": jugador.partidos_sancion_restantes}


def estadisticas_facultad(facultad: Facultad) -> dict:
    equipos = list(Equipo.objects.filter(facultad=facultad).select_related("facultad").order_by("nombre"))
    filas, totales, campeonatos = [], defaultdict(int), set()
    for e in equipos:
        r = rendimiento_de_equipo(e.pk)
        campeonatos.update(r["campeonatos"])
        filas.append({"equipo": e.nombre, **{k: r[k] for k in ("pj", "pg", "pe", "pp", "gf", "gc", "dg", "puntos")}})
        for k in ("pj", "pg", "pe", "pp", "gf", "gc"):
            totales[k] += r[k]
    por_jugador = _incidencias_por_jugador(Q(jugador__equipo__facultad=facultad))
    nombres = {j.pk: j for j in FichaJugador.objects.filter(equipo__facultad=facultad).select_related("equipo")}
    goleadores = sorted(
        ({"jugador": f"{nombres[k].nombre} {nombres[k].apellido}", "equipo": nombres[k].equipo.nombre, "goles": v["goles"]}
         for k, v in por_jugador.items() if v["goles"] and k in nombres),
        key=lambda f: -f["goles"])[:10]
    return {
        "facultad": facultad.nombre, "sigla": facultad.sigla, "equipos": filas, "campeonatos": sorted(campeonatos),
        "totales": {**totales, "dg": totales["gf"] - totales["gc"], "equipos": len(equipos),
                    "jugadores": len(nombres),
                    "amarillas": sum(v["amarillas"] for k, v in por_jugador.items() if k in nombres),
                    "rojas": sum(v["rojas"] for k, v in por_jugador.items() if k in nombres)},
        "goleadores": goleadores,
    }
