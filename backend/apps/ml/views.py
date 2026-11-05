"""
apps/ml/views.py
CU14 — Tablero de predicciones
CU15 — Riesgo climático
CU16 — Predicción de resultados
CU18 — Recomendaciones de actividades (Groq AI)
CU19 — Bitácora
CU20 — Predicción de asistencia
"""
import logging

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.users.roles import es_admin
from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from apps.users.permissions import (
    EsAdmin,
    EsAdminUOrganizador,
    EsAdminUOrganizadorODelegado,
)
from apps.fixture.models import Partido
from .models import PrediccionAsistencia, RiesgoClimatico
from .serializers import (
    PrediccionPartidoSerializer, PrediccionAsistenciaSerializer,
    RiesgoClimaticoSerializer,
)
from .services.predictor import PredictorResultados, informe_modelo
from .services.predictor import entrenar as predictor_entrenar
from .services.asistencia import estimar_asistencia
from .services.recomendaciones import acciones_sugeridas
from .services.clima import ServicioClima, ultimo_riesgo


logger = logging.getLogger(__name__)


# ── CU14 — Tablero general de predicciones ─────────────────────────────────────

@extend_schema(tags=["ml"])
class TableroPrediccionesView(APIView):
    """CU14 — Tablero con predicciones de todos los partidos próximos de un campeonato."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [EsAdminUOrganizador()]
        return [EsAdminUOrganizadorODelegado()]

    @extend_schema(
        summary="CU14 — Tablero de predicciones del campeonato",
        parameters=[OpenApiParameter("campeonato", int, required=True)],
    )
    def get(self, request):
        return self._consultar(request, persistir=False)

    def post(self, request):
        return self._consultar(request, persistir=True)

    def _consultar(self, request, *, persistir):
        campeonato_id = request.data.get("campeonato") if persistir else None
        campeonato_id = campeonato_id or request.query_params.get("campeonato")
        if not campeonato_id:
            return Response({"error": "Parámetro 'campeonato' requerido."},
                            status=status.HTTP_400_BAD_REQUEST)

        partidos = Partido.objects.filter(
            campeonato_id=campeonato_id,
            estado=Partido.Estado.PROGRAMADO,
            equipo_local__isnull=False,
            equipo_visitante__isnull=False,
        ).select_related(
            "equipo_local", "equipo_visitante", "prediccion"
        ).order_by("fecha_hora")[:20]

        predictor = PredictorResultados()
        resultado = []

        for p in partidos:
            pred = predictor.predecir(p, persistir=persistir)

            probs = {
                "local":    pred.prob_victoria_local,
                "empate":   pred.prob_empate,
                "visitante": pred.prob_victoria_visit,
            }
            resultado.append({
                "partido_id":        p.id,
                "local":             p.equipo_local.nombre,
                "visitante":         p.equipo_visitante.nombre,
                "fecha_hora":        p.fecha_hora,
                "prob_local":        round(pred.prob_victoria_local * 100, 1),
                "prob_empate":       round(pred.prob_empate * 100, 1),
                "prob_visitante":    round(pred.prob_victoria_visit * 100, 1),
                "resultado_probable": max(probs, key=probs.get),
                "confianza":         round(pred.confianza * 100, 1),
                "datos_suficientes": pred.datos_suficientes,
                "modelo":            pred.modelo_version,
            })

        if persistir:
            registrar(
                Bitacora.Accion.ML_PRED,
                request=request,
                modulo="campeonato",
                objeto_id=campeonato_id,
                descripcion="Predicciones del campeonato generadas.",
                detalle={"partidos": len(resultado)},
            )
        else:
            logger.info(
                "Consulta del tablero de predicciones.",
                extra={
                    "campeonato_id": campeonato_id,
                    "partidos": len(resultado),
                },
            )
        return Response(resultado)


# ── CU16 — Predicción individual ───────────────────────────────────────────────

@extend_schema(tags=["ml"])
class PrediccionPartidoView(APIView):
    """CU16 — Predicción de resultado de un partido específico."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [EsAdminUOrganizador()]
        return [EsAdminUOrganizadorODelegado()]

    @extend_schema(summary="CU16 — Predecir resultado de un partido")
    def get(self, request, partido_id):
        return self._predecir(request, partido_id, persistir=False)

    def post(self, request, partido_id):
        return self._predecir(request, partido_id, persistir=True)

    def _predecir(self, request, partido_id, *, persistir):
        try:
            partido = Partido.objects.select_related(
                "equipo_local", "equipo_visitante", "campeonato"
            ).get(pk=partido_id)
        except Partido.DoesNotExist:
            return Response({"error": "Partido no encontrado."},
                            status=status.HTTP_404_NOT_FOUND)

        if partido.equipo_local_id is None or partido.equipo_visitante_id is None:
            return Response({"error": "El partido aún no tiene los dos equipos definidos."},
                            status=status.HTTP_400_BAD_REQUEST)

        pred = PredictorResultados().predecir(partido, persistir=persistir)
        if persistir:
            registrar(
                Bitacora.Accion.ML_PRED,
                request=request,
                modulo="partido",
                objeto_id=partido.pk,
                descripcion="Predicción del resultado del partido generada.",
            )
        else:
            logger.info(
                "Consulta de predicción de partido.",
                extra={"partido_id": partido.pk},
            )
        return Response(PrediccionPartidoSerializer(pred).data)


# ── CU15 — Riesgo climático ────────────────────────────────────────────────────

@extend_schema(tags=["ml"])
class RiesgoClimaticoView(APIView):
    """CU15 — Pronóstico de riesgo climático para un partido."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [EsAdminUOrganizador()]
        return [EsAdminUOrganizadorODelegado()]

    @extend_schema(summary="CU15 — Riesgo climático del partido")
    def get(self, request, partido_id):
        return self._consultar(request, partido_id, persistir=False)

    def post(self, request, partido_id):
        return self._consultar(request, partido_id, persistir=True)

    def _consultar(self, request, partido_id, *, persistir):
        try:
            partido = Partido.objects.select_related("cancha").get(pk=partido_id)
        except Partido.DoesNotExist:
            return Response({"error": "Partido no encontrado."},
                            status=status.HTTP_404_NOT_FOUND)

        if partido.equipo_local_id is None or partido.equipo_visitante_id is None:
            return Response({"error": "El partido aún no tiene los dos equipos definidos."},
                            status=status.HTTP_400_BAD_REQUEST)

        if not persistir:
            # F6-07: el GET no consulta la red ni escribe; muestra el último pronóstico guardado.
            riesgo = ultimo_riesgo(partido)
            if riesgo is None:
                return Response({
                    "partido": partido.pk, "nivel_riesgo": RiesgoClimatico.NivelRiesgo.SIN_DATOS, "calculado": False,
                    "descripcion": "Aún no se calculó el pronóstico de este partido.",
                    "recomendacion": "Se actualiza automáticamente; un organizador puede pedirlo ahora.",
                    "fuente_api": "N/A", "consultado_en": None,
                })
            return Response({**RiesgoClimaticoSerializer(riesgo).data, "calculado": True})

        riesgo = ServicioClima().consultar(partido, persistir=True)
        registrar(
            Bitacora.Accion.ML_PRED,
            request=request,
            modulo="partido",
            objeto_id=partido.pk,
            descripcion="Pronóstico de riesgo climático actualizado.",
            detalle={"nivel": riesgo.nivel_riesgo},
        )
        return Response({**RiesgoClimaticoSerializer(riesgo).data, "calculado": riesgo.nivel_riesgo != "SIN_DATOS"})


# ── CU20 — Predicción de asistencia ───────────────────────────────────────────

@extend_schema(tags=["ml"])
class PrediccionAsistenciaView(APIView):
    """CU20 — Estima asistencia de espectadores para un partido."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [EsAdminUOrganizador()]
        return [EsAdminUOrganizadorODelegado()]

    @extend_schema(summary="CU20 — Predicción de asistencia")
    def get(self, request, partido_id):
        return self._predecir(request, partido_id, persistir=False)

    def post(self, request, partido_id):
        return self._predecir(request, partido_id, persistir=True)

    def _predecir(self, request, partido_id, *, persistir):
        try:
            partido = Partido.objects.select_related(
                "equipo_local", "equipo_visitante",
                "campeonato", "cancha",
            ).get(pk=partido_id)
        except Partido.DoesNotExist:
            return Response({"error": "Partido no encontrado."},
                            status=status.HTTP_404_NOT_FOUND)

        if partido.equipo_local_id is None or partido.equipo_visitante_id is None:
            return Response({"error": "El partido aún no tiene los dos equipos definidos."},
                            status=status.HTTP_400_BAD_REQUEST)

        valores = estimar_asistencia(partido)
        if persistir:
            pred, _ = PrediccionAsistencia.objects.update_or_create(
                partido=partido,
                defaults=valores,
            )
        else:
            pred = PrediccionAsistencia(partido=partido, **valores)
        if persistir:
            registrar(
                Bitacora.Accion.ML_PRED,
                request=request,
                modulo="partido",
                objeto_id=partido.pk,
                descripcion="Predicción de asistencia generada.",
            )
        else:
            logger.info(
                "Consulta de predicción de asistencia.",
                extra={"partido_id": partido.pk},
            )
        return Response(PrediccionAsistenciaSerializer(pred).data)


# ── CU18 — Recomendaciones con Groq AI ────────────────────────────────────────

@extend_schema(tags=["ml"])
class RecomendacionesView(APIView):
    """CU18 — Acciones sugeridas para organizar los torneos, calculadas con datos reales."""
    permission_classes = [EsAdminUOrganizador]

    @extend_schema(summary="CU18 — Acciones sugeridas para el organizador")
    def get(self, request):
        acciones = acciones_sugeridas()
        return Response({"acciones": acciones, "total": len(acciones), "fuente": "datos del sistema"})


# ── Entrenamiento del modelo ML ────────────────────────────────────────────────

@extend_schema(tags=["ml"])
class EntrenarModeloView(APIView):
    """Entrena el predictor de resultados con todo el historial y registra el informe (F6-01)."""
    permission_classes = [EsAdmin]

    @extend_schema(summary="Entrenar el predictor de resultados (solo administrador)")
    def post(self, request):
        resultado = predictor_entrenar()
        entrenado = bool(resultado.get("entrenado"))
        registrar(
            Bitacora.Accion.ML_PRED,
            request=request,
            modulo="ml",
            descripcion=("Predictor de resultados entrenado." if entrenado
                         else "Entrenamiento del predictor omitido por datos insuficientes."),
            detalle={"version": resultado.get("version"), "partidos": resultado.get("partidos"),
                     "activo": resultado.get("activo")},
            resultado=Bitacora.Resultado.OK if entrenado else Bitacora.Resultado.ERROR,
        )
        return Response(resultado, status=status.HTTP_200_OK if entrenado else status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Estado e informe del predictor de resultados")
    def get(self, request):
        return Response(informe_modelo())

    def get_permissions(self):
        return [EsAdminUOrganizador()] if self.request.method == "GET" else [EsAdmin()]


# ── Puntuador de asignaciones (RF11) ───────────────────────────────────────────

@extend_schema(tags=["ml"])
class ModeloAsignacionView(APIView):
    """Estado del modelo que puntúa las asignaciones del fixture (versión y métricas)."""
    permission_classes = [EsAdminUOrganizador]

    @extend_schema(summary="RF11 — Estado del modelo de asignación de fixture")
    def get(self, request):
        from .services.asignacion_scorer import info_modelo
        from .models import MuestraAsignacion

        return Response({
            **info_modelo(),
            "muestras_totales": MuestraAsignacion.objects.count(),
            "muestras_reales": MuestraAsignacion.objects.filter(origen="REAL").count(),
        })

    @extend_schema(summary="RF11 — Reentrenar el modelo de asignación con el historial real")
    def post(self, request):
        from .services.asignacion_scorer import ModeloNoDisponible, reentrenar

        if not es_admin(request.user):
            raise PermissionDenied("Solo un administrador puede reentrenar el modelo.")
        try:
            scorer = reentrenar()
        except ModeloNoDisponible as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        registrar(
            Bitacora.Accion.ML_PRED,
            request=request,
            modulo="ml",
            descripcion="Modelo de asignación de fixture reentrenado.",
            detalle={"version": scorer.version, "exactitud": scorer.metricas["exactitud"],
                     "muestras": scorer.metricas["muestras"]},
        )
        return Response({"entrenado": True, **scorer.info()})
