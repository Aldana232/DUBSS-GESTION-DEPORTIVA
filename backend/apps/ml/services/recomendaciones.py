"""
apps/ml/services/recomendaciones.py
CU18 — Acciones sugeridas para el equipo organizador, calculadas SOLO con datos reales del sistema.
(Antes devolvía texto inventado —clases y horarios que no existen—; eso no es aceptable en producción.)
"""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.deportes.models import Campeonato, Inscripcion
from apps.fixture.models import Partido
from apps.ml.models import RiesgoClimatico
from apps.quejas.models import Queja

ALTA, MEDIA, BAJA = "ALTA", "MEDIA", "BAJA"


def acciones_sugeridas() -> list[dict]:
    ahora = timezone.now()
    acciones: list[dict] = []

    def agregar(prioridad, mensaje, enlace):
        acciones.append({"prioridad": prioridad, "mensaje": mensaje, "enlace": enlace})

    for p in Partido.objects.filter(
        estado=Partido.Estado.PROGRAMADO, fecha_hora__gte=ahora, fecha_hora__lte=ahora + timedelta(hours=48),
        riesgos_climaticos__nivel_riesgo__in=[RiesgoClimatico.NivelRiesgo.ALTO, RiesgoClimatico.NivelRiesgo.CRITICO],
    ).select_related("equipo_local", "equipo_visitante").distinct():
        agregar(ALTA, f"Riesgo climático alto: {p.equipo_local} vs {p.equipo_visitante} "
                      f"({timezone.localtime(p.fecha_hora):%d/%m %H:%M}). Considera reprogramar.", f"/gestion/partidos/{p.pk}")

    for q in Queja.objects.filter(estado=Queja.Estado.ABIERTA).select_related("encuentro__campeonato")[:5]:
        agregar(ALTA, f"Queja sin responder en «{q.encuentro.campeonato.nombre}».", "/gestion/quejas")

    atrasados = Partido.objects.filter(
        estado=Partido.Estado.PROGRAMADO, fecha_hora_fin__lt=ahora - timedelta(hours=12),
        campeonato__estado=Campeonato.Estado.EN_CURSO,
    ).select_related("campeonato")
    for nombre in sorted({p.campeonato.nombre for p in atrasados}):
        n = atrasados.filter(campeonato__nombre=nombre).count()
        agregar(ALTA, f"{n} partido(s) de «{nombre}» ya terminaron y no tienen resultado registrado.", "/gestion/fixture")

    pendientes = Inscripcion.objects.filter(estado=Inscripcion.Estado.PENDIENTE,
                                            campeonato__estado=Campeonato.Estado.INSCRIPCIONES).count()
    if pendientes:
        agregar(MEDIA, f"{pendientes} solicitud(es) de inscripción esperan tu revisión.", "/gestion/inscripciones")

    for c in Campeonato.objects.filter(estado=Campeonato.Estado.INSCRIPCION_CERRADA):
        if not c.partidos.exists():
            agregar(MEDIA, f"«{c.nombre}» tiene las inscripciones cerradas pero aún no tiene fixture.", f"/gestion/campeonatos/{c.pk}")
        else:
            agregar(MEDIA, f"«{c.nombre}» tiene el fixture en borrador: revísalo e inicia el campeonato para publicarlo.", f"/gestion/campeonatos/{c.pk}")

    for c in Campeonato.objects.filter(estado=Campeonato.Estado.INSCRIPCIONES, fecha_cierre_inscripcion__isnull=False,
                                       fecha_cierre_inscripcion__lt=ahora):
        agregar(MEDIA, f"El plazo de inscripción de «{c.nombre}» venció: ciérralas para generar el fixture.", f"/gestion/campeonatos/{c.pk}")

    orden = {ALTA: 0, MEDIA: 1, BAJA: 2}
    return sorted(acciones, key=lambda a: orden[a["prioridad"]])
