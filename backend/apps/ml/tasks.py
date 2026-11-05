"""
apps/ml/tasks.py
F6-03 / F6-07 — Pronóstico climático programado y reentrenamiento periódico.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from apps.deportes.models import Campeonato
from apps.fixture.models import Partido
from apps.ml.models import ModeloML, MuestraAsignacion, RiesgoClimatico
from apps.ml.services import asignacion_scorer, predictor
from apps.ml.services.clima import ServicioClima
from apps.notificaciones.services import notificar_usuarios

logger = logging.getLogger(__name__)
GRAVES = (RiesgoClimatico.NivelRiesgo.ALTO, RiesgoClimatico.NivelRiesgo.CRITICO)


@shared_task(name="ml.actualizar_riesgo_climatico")
def actualizar_riesgo_climatico() -> dict:
    """
    Actualiza el pronóstico de los partidos de las próximas 72 h y avisa a los delegados solo cuando
    el riesgo EMPEORA a alto/crítico (no repite el aviso si el nivel no cambió).
    """
    ahora = timezone.now()
    partidos = Partido.objects.filter(
        estado=Partido.Estado.PROGRAMADO, campeonato__estado=Campeonato.Estado.EN_CURSO,
        equipo_local__isnull=False, equipo_visitante__isnull=False,
        fecha_hora__gt=ahora, fecha_hora__lte=ahora + timedelta(hours=72),
    ).select_related("equipo_local__delegado", "equipo_visitante__delegado", "cancha")
    servicio, actualizados, avisos = ServicioClima(), 0, 0
    for partido in partidos:
        anterior = partido.riesgos_climaticos.first()
        riesgo = servicio.consultar(partido, persistir=True)
        if riesgo.nivel_riesgo == RiesgoClimatico.NivelRiesgo.SIN_DATOS:
            continue
        actualizados += 1
        if riesgo.nivel_riesgo in GRAVES and (anterior is None or anterior.nivel_riesgo not in GRAVES):
            notificar_usuarios(
                [partido.equipo_local.delegado, partido.equipo_visitante.delegado],
                "Posible cambio por clima",
                f"{partido.equipo_local} vs {partido.equipo_visitante} "
                f"({timezone.localtime(partido.fecha_hora):%d/%m %H:%M}): {riesgo.recomendacion}",
                {"partido_id": partido.pk},
            )
            avisos += 1
    return {"actualizados": actualizados, "avisos": avisos}


@shared_task(name="ml.reentrenar_modelos")
def reentrenar_modelos() -> dict:
    """
    Reentrena solo si hay datos nuevos: el predictor cuando cambia la huella de los partidos jugados,
    y el puntuador de horarios cuando hay partidos reales sin muestrear. Repetir la tarea no cambia nada.
    """
    resumen: dict = {}
    _, _, _, huella = predictor.construir_dataset()
    ultimo = ModeloML.objects.filter(nombre=predictor.NOMBRE_MODELO).first()
    if ultimo is None or ultimo.hash_datos != huella:
        r = predictor.entrenar()
        resumen["predictor"] = {"entrenado": r["entrenado"], "version": r.get("version"), "activo": r.get("activo")}
    else:
        resumen["predictor"] = {"entrenado": False, "motivo": "sin datos nuevos"}

    nuevas = asignacion_scorer.sincronizar_muestras_reales()
    if nuevas:
        try:
            scorer = asignacion_scorer.reentrenar()
            resumen["asignacion"] = {"reentrenado": True, "version": scorer.version, "muestras_nuevas": nuevas}
        except asignacion_scorer.ModeloNoDisponible as e:
            resumen["asignacion"] = {"reentrenado": False, "motivo": str(e)}
    else:
        resumen["asignacion"] = {"reentrenado": False, "motivo": "sin partidos reales nuevos",
                                 "muestras_reales": MuestraAsignacion.objects.filter(origen="REAL").count()}
    registrar(Bitacora.Accion.ML_PRED, modulo="ml", descripcion="Reentrenamiento programado de los modelos.", detalle=resumen)
    return resumen


@shared_task(name="ml.revisar_resultados_atipicos")
def revisar_resultados_atipicos() -> dict:
    """
    F7-08 — Busca marcadores raros en el historial y avisa a la administración SOLO de los nuevos
    (cada alerta se guarda una vez por partido, así que repetir la tarea no repite el aviso).
    """
    from apps.ml.services import atipicos
    from apps.users.models import Usuario

    nuevas = atipicos.escanear()
    if nuevas:
        admins = list(Usuario.objects.filter(is_active=True, rol__in=[Usuario.Rol.ADMIN_DUBSS, Usuario.Rol.SUPERADMIN]))
        detalle = "; ".join(a.motivo for a in nuevas[:3])
        notificar_usuarios(admins, "Resultado atípico por revisar", f"Se detectaron {len(nuevas)} marcador(es) inusual(es). {detalle}"[:480])
    return {"nuevas": len(nuevas)}
