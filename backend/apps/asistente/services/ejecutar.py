"""
apps/asistente/services/ejecutar.py
F6-06 — Ejecuta una orden YA validada y confirmada por la persona. Solo lecturas: el asistente nunca modifica datos.
Para los reportes reutiliza los generadores existentes (PDF/Excel) indicando qué descargar.
"""
from __future__ import annotations


from django.db.models import Q
from django.utils import timezone

from apps.deportes.models import Campeonato, Equipo, FichaJugador
from apps.fixture.models import Partido, TablaPosiciones
from apps.fixture.services.estadisticas import estadisticas_campeonato
from apps.reportes.estadisticas import estadisticas_equipo, estadisticas_jugador

LIMITE_PARTIDOS = 10


def _descarga(recurso: str, objeto, formato: str, nombre: str) -> dict:
    return {"tipo": "descarga", "recurso": recurso, "id": objeto.pk, "formato": formato, "nombre": nombre}


def _tabla(campeonato: Campeonato) -> dict:
    filas = TablaPosiciones.objects.filter(campeonato=campeonato).select_related("equipo").order_by("posicion", "-puntos")
    return {"tipo": "tabla", "campeonato": campeonato.nombre, "filas": [
        {"posicion": f.posicion, "equipo": f.equipo.nombre, "pj": f.pj, "pg": f.pg, "pe": f.pe, "pp": f.pp,
         "gf": f.gf, "gc": f.gc, "puntos": f.puntos} for f in filas]}


def _proximos(campeonato: Campeonato | None, equipo: Equipo | None) -> dict:
    qs = Partido.objects.filter(
        estado=Partido.Estado.PROGRAMADO, fecha_hora__gte=timezone.now(), equipo_local__isnull=False,
        equipo_visitante__isnull=False,
        campeonato__estado__in=[Campeonato.Estado.EN_CURSO],            # solo fixtures publicados
    ).select_related("equipo_local", "equipo_visitante", "cancha", "campeonato").order_by("fecha_hora")
    if campeonato:
        qs = qs.filter(campeonato=campeonato)
    if equipo:
        qs = qs.filter(Q(equipo_local=equipo) | Q(equipo_visitante=equipo))
    return {"tipo": "partidos", "partidos": [
        {"id": p.pk, "local": p.equipo_local.nombre, "visitante": p.equipo_visitante.nombre,
         "fecha_hora": timezone.localtime(p.fecha_hora).isoformat(), "cancha": p.cancha.nombre if p.cancha else None,
         "jornada": p.jornada, "campeonato": p.campeonato.nombre} for p in qs[:LIMITE_PARTIDOS]]}


def _resumen(campeonato: Campeonato) -> dict:
    partidos = Partido.objects.filter(campeonato=campeonato)
    lider = TablaPosiciones.objects.filter(campeonato=campeonato, pj__gt=0).select_related("equipo").order_by("posicion").first()
    stats = estadisticas_campeonato(campeonato)
    proximo = (partidos.filter(estado=Partido.Estado.PROGRAMADO, fecha_hora__gte=timezone.now(),
                               campeonato__estado=Campeonato.Estado.EN_CURSO)
               .select_related("equipo_local", "equipo_visitante").order_by("fecha_hora").first())
    return {"tipo": "resumen", "campeonato": campeonato.nombre, "estado": campeonato.get_estado_display(),
            "equipos": campeonato.inscripciones.filter(estado="APROBADA").count(),
            "partidos_jugados": stats["resumen"]["partidos_jugados"], "partidos_total": stats["resumen"]["partidos_total"],
            "goles": stats["resumen"]["goles"], "lider": lider.equipo.nombre if lider else None,
            "goleador": stats["goleadores"][0] if stats["goleadores"] else None,
            "proximo_partido": (f"{proximo.equipo_local} vs {proximo.equipo_visitante} — "
                                f"{timezone.localtime(proximo.fecha_hora):%d/%m %H:%M}") if proximo else None}


def ejecutar(intencion: str, *, formato: str | None, campeonato: Campeonato | None = None,
             equipo: Equipo | None = None, jugador: FichaJugador | None = None) -> dict:
    if intencion == "reporte_campeonato":
        return _descarga("campeonato", campeonato, formato or "pdf", campeonato.nombre)
    if intencion == "tabla_posiciones":
        return _tabla(campeonato)
    if intencion == "resumen_torneo":
        return _resumen(campeonato)
    if intencion == "proximos_partidos":
        return _proximos(campeonato, equipo)
    if intencion == "estadisticas_equipo":
        if formato:
            return _descarga("equipo", equipo, formato, equipo.nombre)
        return {"tipo": "estadisticas_equipo", "datos": estadisticas_equipo(equipo)}
    if intencion == "estadisticas_jugador":
        if formato:
            return _descarga("jugador", jugador, formato, f"{jugador.nombre} {jugador.apellido}")
        return {"tipo": "estadisticas_jugador", "datos": estadisticas_jugador(jugador)}
    raise ValueError(f"Intención no soportada: {intencion}")

