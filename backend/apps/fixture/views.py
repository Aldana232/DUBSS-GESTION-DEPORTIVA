"""
apps/fixture/views.py
CU08 — Creación de fixture
CU10 — Visualización de calendarios
CU11 — Registro y corrección de resultados
CU12 — Registro de incidencias
CU13 — Tabla de posiciones
"""
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from apps.notificaciones.services import notificar_usuarios
from apps.users.roles import es_admin, es_organizador
from apps.users.permissions import (
    EsAdminUOrganizador,
    EsLecturaPublica,
)
from apps.deportes.models import Campeonato
from .idempotencia import ejecutar_idempotente
from .models import Partido, Resultado, TablaPosiciones
from .serializers import (
    PartidoSerializer, PartidoResumenSerializer,
    ResultadoSerializer, IncidenciaSerializer,
    TablaPosicionesSerializer,
)
from .services import estadisticas, metricas, resultados, sanciones, tabla
from .services.fixture_generator import FixtureConflicto, FixtureError, FixtureGenerator


class ResultadoYaRegistrado(APIException):
    """409: otra persona ya cerró el partido (típico al sincronizar la planilla sin conexión)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Este partido ya tiene resultado registrado. Usa PATCH para corregirlo."
    default_code = "resultado_ya_registrado"


@extend_schema(tags=["fixture"])
class PartidoViewSet(viewsets.ModelViewSet):
    """CU10 — Calendarios / listado de partidos."""
    queryset = Partido.objects.select_related(
        "equipo_local", "equipo_visitante", "cancha",
        "arbitro", "campeonato", "resultado",
    ).prefetch_related("incidencias").order_by("fecha_hora")

    filterset_fields = ["campeonato", "estado", "jornada", "equipo_local", "equipo_visitante"]
    search_fields    = ["equipo_local__nombre", "equipo_visitante__nombre"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not (es_admin(self.request.user) or es_organizador(self.request.user)):
            # RF11: el fixture es un borrador hasta que el campeonato inicia; solo entonces se publica.
            queryset = queryset.filter(
                campeonato__estado__in=[Campeonato.Estado.EN_CURSO, Campeonato.Estado.FINALIZADO]
            )
        equipo = self.request.query_params.get("equipo")
        if equipo and equipo.isdigit():
            queryset = queryset.filter(Q(equipo_local_id=equipo) | Q(equipo_visitante_id=equipo))
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return PartidoResumenSerializer
        return PartidoSerializer

    def get_permissions(self):
        if self.action in (
            "create",
            "update",
            "partial_update",
            "destroy",
            "registrar_resultado",
            "registrar_incidencia",
        ):
            return [EsAdminUOrganizador()]
        return [EsLecturaPublica()]

    # ── Alta / reprogramación (F3-09) ─────────────────────────────────────────
    def perform_create(self, serializer):
        partido = serializer.save()
        registrar(
            Bitacora.Accion.CREAR,
            request=self.request,
            modulo="partido",
            objeto_id=partido.pk,
            descripcion="Partido programado manualmente.",
            detalle={"cancha": partido.cancha_id, "fecha_hora": timezone.localtime(partido.fecha_hora).isoformat()},
        )

    def perform_update(self, serializer):
        anterior = {
            "fecha_hora": serializer.instance.fecha_hora,
            "cancha": serializer.instance.cancha,
            "duracion_min": serializer.instance.duracion_min,
        }
        partido = serializer.save()
        nuevo = {
            "fecha_hora": partido.fecha_hora,
            "cancha": partido.cancha,
            "duracion_min": partido.duracion_min,
        }
        if anterior == nuevo:
            registrar(
                Bitacora.Accion.EDITAR, request=self.request, modulo="partido",
                objeto_id=partido.pk, descripcion="Partido actualizado.",
            )
            return

        def texto(datos):
            cancha = datos["cancha"].nombre if datos["cancha"] else "sin cancha"
            return f"{timezone.localtime(datos['fecha_hora']):%d/%m/%Y %H:%M} en {cancha}"

        registrar(
            Bitacora.Accion.EDITAR,
            request=self.request,
            modulo="partido",
            objeto_id=partido.pk,
            descripcion="Partido reprogramado.",
            detalle={
                "anterior": {
                    "fecha_hora": timezone.localtime(anterior["fecha_hora"]).isoformat(),
                    "cancha": anterior["cancha"].pk if anterior["cancha"] else None,
                },
                "nuevo": {
                    "fecha_hora": timezone.localtime(partido.fecha_hora).isoformat(),
                    "cancha": partido.cancha_id,
                },
            },
        )
        equipos = [e for e in (partido.equipo_local, partido.equipo_visitante) if e]
        notificar_usuarios(
            [e.delegado for e in equipos],
            "Partido reprogramado",
            f"El partido {partido} cambió de {texto(anterior)} a {texto(nuevo)}.",
        )

    # ── CU11: Registrar / corregir / eliminar resultado ───────────────────────
    @extend_schema(
        summary="CU11 — Registrar (POST), corregir (PATCH) o eliminar (DELETE) el resultado",
        request=ResultadoSerializer,
    )
    @action(detail=True, methods=["post", "patch", "delete"], url_path="resultado",
            permission_classes=[EsAdminUOrganizador])
    def registrar_resultado(self, request, pk=None):
        if request.method == "POST":
            return ejecutar_idempotente(request, lambda: self._procesar_resultado(request, pk))
        return self._procesar_resultado(request, pk)

    def _procesar_resultado(self, request, pk):
        partido = self.get_object()
        metodo = request.method

        if metodo == "DELETE":
            motivo = (request.data.get("motivo") or "").strip()
            if not motivo:
                raise ValidationError({"motivo": "Indica el motivo de la eliminación."})
            if not Resultado.objects.filter(partido=partido).exists():
                raise ValidationError({"detail": "El partido no tiene resultado registrado."})
            anterior = resultados.eliminar_resultado(partido)
            registrar(
                Bitacora.Accion.CORREGIR_RESULTADO,
                request=request,
                modulo="partido",
                objeto_id=partido.pk,
                descripcion="Resultado eliminado.",
                detalle={"operacion": "eliminar", "motivo": motivo, "anterior": anterior},
            )
            return Response(status=status.HTTP_204_NO_CONTENT)

        existente = Resultado.objects.filter(partido=partido).first()
        if metodo == "POST" and existente is not None:
            raise ResultadoYaRegistrado()
        if metodo == "PATCH" and existente is None:
            raise ValidationError({"detail": "El partido aún no tiene resultado para corregir."})

        serializer = ResultadoSerializer(
            existente,
            data=request.data,
            partial=(metodo == "PATCH"),
            context={"request": request, "partido": partido, "corregir": metodo == "PATCH"},
        )
        serializer.is_valid(raise_exception=True)

        if metodo == "POST":
            resultado = resultados.registrar_resultado(
                partido, serializer.validated_data, request.user
            )
            registrar(
                Bitacora.Accion.REGISTRAR_RESULTADO,
                request=request,
                modulo="partido",
                objeto_id=partido.pk,
                descripcion="Resultado registrado.",
                detalle={
                    "goles_local": resultado.goles_local,
                    "goles_visitante": resultado.goles_visitante,
                    "walkover": resultado.walkover,
                },
            )
            return Response(ResultadoSerializer(resultado).data,
                            status=status.HTTP_201_CREATED)

        resultado, anterior = resultados.corregir_resultado(
            partido, serializer.validated_data
        )
        registrar(
            Bitacora.Accion.CORREGIR_RESULTADO,
            request=request,
            modulo="partido",
            objeto_id=partido.pk,
            descripcion="Resultado corregido.",
            detalle={
                "motivo": serializer.motivo,
                "anterior": anterior,
                "nuevo": resultados.resumen(resultado),
            },
        )
        return Response(ResultadoSerializer(resultado).data)

    # ── CU12: Registrar incidencia ────────────────────────────────────────────
    @extend_schema(
        summary="CU12 — Registrar incidencia del partido",
        request=IncidenciaSerializer,
    )
    @action(detail=True, methods=["post"], url_path="incidencia",
            permission_classes=[EsAdminUOrganizador])
    def registrar_incidencia(self, request, pk=None):
        return ejecutar_idempotente(request, lambda: self._procesar_incidencia(request, pk))

    def _procesar_incidencia(self, request, pk):
        partido    = self.get_object()
        serializer = IncidenciaSerializer(
            data=request.data, context={"request": request, "partido": partido}
        )
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            incidencia = serializer.save(partido=partido)
            partidos_sancion = sanciones.aplicar_sancion(incidencia)
        registrar(
            Bitacora.Accion.REGISTRAR_INCIDENCIA,
            request=request,
            modulo="partido",
            objeto_id=partido.pk,
            descripcion="Incidencia registrada en el partido.",
            detalle={
                "tipo": incidencia.tipo,
                "minuto": incidencia.minuto,
                "incidencia_id": incidencia.pk,
                "partidos_sancion": partidos_sancion,
            },
        )
        datos = dict(IncidenciaSerializer(incidencia).data)
        datos["partidos_sancion"] = partidos_sancion
        return Response(datos, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        partido = self.get_object()
        if Resultado.objects.filter(partido=partido).exists():
            raise ValidationError(
                {"detail": "El partido tiene resultado registrado; elimina primero el resultado."}
            )
        campeonato = partido.campeonato
        with transaction.atomic():
            partido.delete()
            tabla.actualizar_historial(campeonato)
        registrar(
            Bitacora.Accion.GENERAR_FIXTURE,
            request=request,
            modulo="campeonato",
            objeto_id=campeonato.pk,
            descripcion="Partido eliminado del fixture.",
            detalle={"operacion": "eliminar", "cantidad_partidos": 1},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class GenerarFixtureSerializer(serializers.Serializer):
    campeonato_id = serializers.IntegerField()
    usar_ml = serializers.BooleanField(required=False, default=False)
    sembrar_con_ml = serializers.BooleanField(required=False, default=False)
    hora_inicio = serializers.RegexField(
        r"^\d{1,2}:\d{2}$", required=False, default="08:00",
        error_messages={"invalid": "La hora debe tener el formato HH:MM."},
    )
    dias_entre_jornadas = serializers.IntegerField(required=False, default=7, min_value=1)
    doble_vuelta = serializers.BooleanField(required=False, default=False)


@extend_schema(tags=["fixture"])
class GenerarFixtureView(APIView):
    """CU08 — Generar fixture automático de un campeonato."""
    permission_classes = [EsAdminUOrganizador]

    @extend_schema(
        summary="CU08 — Generar fixture del campeonato",
        request=GenerarFixtureSerializer,
    )
    def post(self, request):
        # Acepta body JSON o query string (Swagger).
        entrada = {**request.query_params.dict(), **request.data}
        serializer = GenerarFixtureSerializer(data=entrada)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        campeonato_id = datos["campeonato_id"]

        partidos_previos = Partido.objects.filter(campeonato_id=campeonato_id).count()
        try:
            generador = FixtureGenerator(
                campeonato_id=campeonato_id,
                hora_inicio=datos["hora_inicio"],
                dias_entre_jornadas=datos["dias_entre_jornadas"],
                doble_vuelta=datos["doble_vuelta"],
            )
            partidos = generador.generar(usar_ml=datos["usar_ml"], sembrar_con_ml=datos["sembrar_con_ml"])
        except FixtureConflicto as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except FixtureError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        resultado = getattr(generador, "resultado", None) or {}
        por_ml = bool(resultado.get("generado_por_ml"))
        registrar(
            Bitacora.Accion.GENERAR_FIXTURE,
            request=request,
            modulo="campeonato",
            objeto_id=campeonato_id,
            descripcion="Fixture generado para el campeonato" + (" con ML." if por_ml else "."),
            detalle={
                "operacion": "generar",
                "cantidad_partidos": len(partidos),
                "partidos_eliminados": partidos_previos,
                "doble_vuelta": datos["doble_vuelta"],
                "generado_por_ml": por_ml,
                **({"siembra_ml": bool((resultado.get("siembra") or {}).get("aplicada"))} if resultado.get("siembra") else {}),
                **({"aviso": resultado["aviso"]} if resultado.get("aviso") else {}),
            },
        )
        return Response(
            {
                "mensaje":          f"Fixture generado: {len(partidos)} partidos creados.",
                "total_partidos":   len(partidos),
                "generado_por_ml":  por_ml,
                "aviso":            resultado.get("aviso", ""),
                "calidad":          resultado.get("calidad"),
                "ml":               resultado.get("ml"),
                "siembra":          resultado.get("siembra"),
                "partidos":         PartidoResumenSerializer(partidos, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["fixture"])
class CalidadFixtureView(APIView):
    """RF11 — Métricas de calidad del fixture de un campeonato (para el organizador)."""
    permission_classes = [EsAdminUOrganizador]

    @extend_schema(summary="Métricas de calidad del fixture", parameters=[OpenApiParameter("campeonato", int, required=True)])
    def get(self, request):
        campeonato_id = request.query_params.get("campeonato", "")
        if not campeonato_id.isdigit():
            return Response({"error": "Parámetro 'campeonato' requerido."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            campeonato = Campeonato.objects.get(pk=campeonato_id)
        except Campeonato.DoesNotExist:
            return Response({"error": "Campeonato no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        partidos = Partido.objects.filter(campeonato=campeonato)
        return Response({
            **metricas.calcular_calidad(campeonato),
            "generado_por_ml": partidos.exists() and not partidos.filter(generado_por_ml=False).exists(),
        })


@extend_schema(tags=["fixture"])
class TablaPosicionesView(APIView):
    """CU13 — Tabla de posiciones de un campeonato."""
    permission_classes = [EsLecturaPublica]

    @extend_schema(
        summary="CU13 — Tabla de posiciones",
        parameters=[
            OpenApiParameter("campeonato", int, required=True,
                             description="ID del campeonato"),
        ],
    )
    def get(self, request):
        campeonato_id = request.query_params.get("campeonato")
        if not campeonato_id:
            return Response(
                {"error": "Parámetro 'campeonato' requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        filas = TablaPosiciones.objects.filter(
            campeonato_id=campeonato_id
        ).select_related("equipo").order_by("posicion", "-puntos", "-gf")

        return Response(TablaPosicionesSerializer(filas, many=True).data)


@extend_schema(tags=["fixture"])
class EstadisticasView(APIView):
    """RF19 — Estadísticas públicas del campeonato (goleadores, tarjetas, resumen)."""
    permission_classes = [EsLecturaPublica]

    @extend_schema(
        summary="Estadísticas del campeonato",
        parameters=[OpenApiParameter("campeonato", int, required=True)],
    )
    def get(self, request):
        campeonato_id = request.query_params.get("campeonato", "")
        if not campeonato_id.isdigit():
            return Response(
                {"error": "Parámetro 'campeonato' requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            campeonato = Campeonato.objects.get(pk=campeonato_id)
        except Campeonato.DoesNotExist:
            return Response({"error": "Campeonato no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(estadisticas.estadisticas_campeonato(campeonato))
