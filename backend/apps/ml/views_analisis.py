"""
apps/ml/views_analisis.py
F7-07 — Niveles de equipos y siembra (K-means).   F7-08 — Resultados atípicos (Isolation Forest).
"""
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from apps.deportes.models import Campeonato
from apps.ml.models import ResultadoAtipico
from apps.ml.services import atipicos, niveles
from apps.users.permissions import EsAdminUOrganizador


class SiembraEntrada(serializers.Serializer):
    campeonato_id = serializers.PrimaryKeyRelatedField(queryset=Campeonato.objects.select_related("categoria__deporte"), source="campeonato")
    grupos = serializers.IntegerField(required=False, min_value=2, max_value=16)


@extend_schema(tags=["ml"])
class CabezasDeSerieView(APIView):
    """F7-07 — Agrupa los equipos inscritos por rendimiento y propone siembra y grupos equilibrados. No modifica nada."""
    permission_classes = [EsAdminUOrganizador]

    @extend_schema(summary="F7-07 — Niveles, cabezas de serie y grupos equilibrados", request=SiembraEntrada)
    def post(self, request):
        s = SiembraEntrada(data=request.data)
        s.is_valid(raise_exception=True)
        campeonato = s.validated_data["campeonato"]
        resultado = niveles.analizar(campeonato, grupos=s.validated_data.get("grupos"))
        registrar(Bitacora.Accion.ML_PRED, request=request, modulo="campeonato", objeto_id=campeonato.pk,
                  descripcion="Análisis de niveles y siembra de equipos.",
                  detalle={"metodo": resultado["metodo"], "equipos": resultado["equipos_total"], "niveles": resultado["k"]})
        return Response(resultado)


class AlertaSerializer(serializers.ModelSerializer):
    partido_id = serializers.IntegerField(read_only=True)
    partido = serializers.SerializerMethodField()
    campeonato = serializers.CharField(source="partido.campeonato.nombre", read_only=True)
    marcador = serializers.SerializerMethodField()
    fecha = serializers.DateTimeField(source="partido.fecha_hora", read_only=True)

    class Meta:
        model = ResultadoAtipico
        fields = ["id", "partido_id", "partido", "campeonato", "marcador", "fecha", "puntaje", "motivo", "detectado_en", "revisado", "revisado_en"]

    def get_partido(self, a) -> str:
        return f"{a.partido.equipo_local.nombre} vs {a.partido.equipo_visitante.nombre}"

    def get_marcador(self, a) -> str:
        r = a.partido.resultado
        return f"{r.goles_local}-{r.goles_visitante}"


@extend_schema(tags=["ml"])
class AtipicosView(APIView):
    """F7-08 — Resultados atípicos detectados (GET) y escaneo manual (POST, solo administración)."""
    permission_classes = [EsAdminUOrganizador]

    @extend_schema(summary="F7-08 — Lista de resultados atípicos")
    def get(self, request):
        qs = ResultadoAtipico.objects.select_related("partido__campeonato", "partido__equipo_local", "partido__equipo_visitante", "partido__resultado")
        if request.query_params.get("revisado") in ("true", "false"):
            qs = qs.filter(revisado=request.query_params["revisado"] == "true")
        return Response({"pendientes": ResultadoAtipico.objects.filter(revisado=False).count(), "resultados": AlertaSerializer(qs[:50], many=True).data})

    @extend_schema(summary="F7-08 — Buscar resultados atípicos ahora")
    def post(self, request):
        if not request.user.es_admin:
            return Response({"detail": "Solo la administración puede lanzar el análisis."}, status=status.HTTP_403_FORBIDDEN)
        nuevas = atipicos.escanear()
        registrar(Bitacora.Accion.ML_PRED, request=request, modulo="ml", descripcion="Búsqueda de resultados atípicos.", detalle={"nuevos": len(nuevas)})
        return Response({"nuevos": len(nuevas), "resultados": AlertaSerializer(nuevas, many=True).data})


@extend_schema(tags=["ml"])
class RevisarAtipicoView(APIView):
    permission_classes = [EsAdminUOrganizador]

    @extend_schema(summary="F7-08 — Marcar una alerta como revisada")
    def post(self, request, pk):
        alerta = ResultadoAtipico.objects.select_related("partido__campeonato", "partido__equipo_local", "partido__equipo_visitante", "partido__resultado").filter(pk=pk).first()
        if alerta is None:
            return Response({"detail": "No existe esa alerta."}, status=status.HTTP_404_NOT_FOUND)
        if not alerta.revisado:
            alerta.revisado, alerta.revisado_por, alerta.revisado_en = True, request.user, timezone.now()
            alerta.save(update_fields=["revisado", "revisado_por", "revisado_en"])
            registrar(Bitacora.Accion.EDITAR, request=request, modulo="partido", objeto_id=alerta.partido_id, descripcion="Alerta de resultado atípico revisada.")
        return Response(AlertaSerializer(alerta).data)
