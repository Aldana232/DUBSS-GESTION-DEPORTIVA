"""
apps/deportes/views.py
CU03, CU04, CU05, CU06, CU09
"""
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.utils import timezone

from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from apps.users.permissions import (
    EsAdmin,
    EsAdminUOrganizador,
    EsAdminUOrganizadorLectura,
    EsAdminUOrganizadorODelegado,
    EsAdminODelegadoDeSuFacultad,
    EsLecturaPublica,
)
from apps.users.roles import es_delegado
from apps.notificaciones.services import notificar_usuarios
from .models import (
    Facultad, RestriccionHorarioFacultad, Deporte, Categoria, Campeonato,
    Equipo, Inscripcion, FichaJugador,
)
from .serializers import (
    FacultadSerializer, RestriccionHorarioFacultadSerializer, DeporteSerializer,
    CategoriaSerializer, CampeonatoSerializer, EquipoSerializer,
    InscripcionSerializer, FichaJugadorSerializer,
)
from .services import (
    errores_transicion_campeonato, evaluar_inscripcion, transiciones_permitidas,
)


@extend_schema(tags=["deportes"])
class FacultadViewSet(viewsets.ModelViewSet):
    queryset = Facultad.objects.all()
    serializer_class = FacultadSerializer
    permission_classes = [EsLecturaPublica]
    search_fields = ["nombre", "sigla"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [EsAdmin()]
        return [EsAdminUOrganizadorLectura()]


@extend_schema(tags=["deportes"])
class RestriccionHorarioFacultadViewSet(viewsets.ModelViewSet):
    queryset = RestriccionHorarioFacultad.objects.select_related("facultad")
    serializer_class = RestriccionHorarioFacultadSerializer
    filterset_fields = ["facultad", "dia_semana"]
    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [EsAdmin()]
        return [EsAdminUOrganizadorLectura()]


@extend_schema(tags=["deportes"])
class DeporteViewSet(viewsets.ModelViewSet):
    """CU05 — CRUD de deportes."""
    queryset           = Deporte.objects.filter(activo=True).order_by("nombre")
    serializer_class   = DeporteSerializer
    permission_classes = [EsLecturaPublica]
    search_fields      = ["nombre"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [EsAdmin()]
        return [EsAdminUOrganizadorLectura()]


@extend_schema(tags=["deportes"])
class CategoriaViewSet(viewsets.ModelViewSet):
    """CU04 — CRUD de categorías."""
    queryset           = Categoria.objects.filter(activa=True).select_related("deporte")
    serializer_class   = CategoriaSerializer
    permission_classes = [EsLecturaPublica]
    filterset_fields   = ["deporte", "genero"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [EsAdmin()]
        return [EsAdminUOrganizadorLectura()]


@extend_schema(tags=["deportes"])
class CampeonatoViewSet(viewsets.ModelViewSet):
    """CU09 — CRUD de campeonatos."""
    queryset = Campeonato.objects.select_related(
        "categoria__deporte", "creado_por"
    ).order_by("-fecha_inicio")
    serializer_class   = CampeonatoSerializer
    filterset_fields   = ["estado", "categoria", "categoria__deporte"]
    search_fields      = ["nombre"]

    def get_permissions(self):
        if self.action in (
            "create",
            "update",
            "partial_update",
            "destroy",
            "cambiar_estado",
        ):
            return [EsAdminUOrganizador()]
        return [EsLecturaPublica()]

    def perform_destroy(self, instance):
        # Un campeonato con actividad (partidos con resultado o en marcha) no se borra: se cancela.
        from apps.fixture.models import Resultado

        if instance.estado not in (Campeonato.Estado.PLANIFICACION, Campeonato.Estado.CANCELADO) \
                or Resultado.objects.filter(partido__campeonato=instance).exists():
            raise ValidationError({
                "detail": "No se puede eliminar un campeonato con actividad. "
                          "Cancélalo para conservar su historial."
            })
        registrar(
            Bitacora.Accion.ELIMINAR,
            request=self.request,
            modulo="campeonato",
            objeto_id=instance.pk,
            descripcion="Campeonato eliminado.",
            detalle={"nombre": instance.nombre, "estado": instance.estado},
        )
        instance.delete()

    @extend_schema(summary="Equipos inscritos en el campeonato")
    @action(detail=True, methods=["get"], url_path="equipos")
    def equipos(self, request, pk=None):
        campeonato = self.get_object()
        equipos = Equipo.objects.filter(
            inscripciones__campeonato=campeonato,
            inscripciones__estado=Inscripcion.Estado.APROBADA,
            estado="ACTIVO",
        ).prefetch_related("jugadores").distinct()
        serializer = EquipoSerializer(equipos, many=True, context={"request": request})
        return Response(serializer.data)

    @extend_schema(summary="Cambiar estado del campeonato (RF10)")
    @action(detail=True, methods=["patch"], url_path="estado",
            permission_classes=[EsAdminUOrganizador])
    def cambiar_estado(self, request, pk=None):
        campeonato = self.get_object()
        anterior   = campeonato.estado
        nuevo      = request.data.get("estado")
        errores    = errores_transicion_campeonato(campeonato, nuevo)
        if errores:
            registrar(
                Bitacora.Accion.CAMBIO_ESTADO,
                request=request,
                modulo="campeonato",
                objeto_id=campeonato.pk,
                descripcion="Cambio de estado rechazado.",
                detalle={"anterior": anterior, "solicitado": str(nuevo), "motivos": errores},
                resultado=Bitacora.Resultado.ERROR,
            )
            raise ValidationError({"estado": errores})
        campeonato.estado = nuevo
        campeonato.save(update_fields=["estado", "actualizado_en"])
        registrar(
            Bitacora.Accion.CAMBIO_ESTADO,
            request=request,
            modulo="campeonato",
            objeto_id=campeonato.pk,
            descripcion="Estado del campeonato actualizado.",
            detalle={"anterior": anterior, "nuevo": nuevo},
        )
        return Response({
            "estado": nuevo,
            "transiciones_permitidas": transiciones_permitidas(nuevo),
            "mensaje": "Estado actualizado.",
        })

    @extend_schema(summary="Historial de posiciones por jornada (RF13)")
    @action(detail=True, methods=["get"], url_path="historial")
    def historial(self, request, pk=None):
        from apps.fixture.services.tabla import historial_por_jornada

        campeonato = self.get_object()
        return Response(historial_por_jornada(campeonato))


@extend_schema(tags=["equipos"])
class EquipoViewSet(viewsets.ModelViewSet):
    """CU03 — Inscripción y gestión de equipos."""
    queryset = Equipo.objects.filter(estado="ACTIVO").select_related(
        "facultad", "delegado"
    ).prefetch_related("jugadores__usuario")
    serializer_class   = EquipoSerializer
    filterset_fields   = ["facultad"]
    search_fields      = ["nombre", "facultad__nombre"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [EsAdminODelegadoDeSuFacultad()]
        return [EsAdminUOrganizadorODelegado()]

    def get_queryset(self):
        queryset = super().get_queryset()
        if es_delegado(self.request.user):
            return queryset.filter(facultad_id=self.request.user.facultad_id)
        return queryset

    def perform_create(self, serializer):
        kwargs = {}
        if es_delegado(self.request.user):
            kwargs = {
                "facultad": self.request.user.facultad,
                "delegado": self.request.user,
            }
        equipo = serializer.save(**kwargs)
        registrar(
            Bitacora.Accion.CREAR,
            request=self.request,
            modulo="equipo",
            objeto_id=equipo.pk,
            descripcion="Equipo creado.",
        )

    def perform_update(self, serializer):
        equipo = serializer.save()
        registrar(
            Bitacora.Accion.EDITAR,
            request=self.request,
            modulo="equipo",
            objeto_id=equipo.pk,
            descripcion="Equipo actualizado.",
        )

    def perform_destroy(self, instance):
        registrar(
            Bitacora.Accion.ELIMINAR,
            request=self.request,
            modulo="equipo",
            objeto_id=instance.pk,
            descripcion="Equipo eliminado.",
        )
        instance.delete()


@extend_schema(tags=["inscripciones"])
class InscripcionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = InscripcionSerializer
    queryset = Inscripcion.objects.select_related(
        "campeonato", "equipo", "equipo__facultad", "validado_por"
    )
    filterset_fields = ["campeonato", "equipo", "estado"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action == "validar":
            return [EsAdminUOrganizador()]
        if self.action == "create":
            return [EsAdminODelegadoDeSuFacultad()]
        return [EsAdminUOrganizadorODelegado()]

    def get_queryset(self):
        queryset = super().get_queryset()
        if es_delegado(self.request.user):
            return queryset.filter(equipo__facultad_id=self.request.user.facultad_id)
        return queryset

    def perform_create(self, serializer):
        inscripcion = serializer.save()
        registrar(
            Bitacora.Accion.CREAR,
            request=self.request,
            modulo="inscripcion",
            objeto_id=inscripcion.pk,
            descripcion="Solicitud de inscripción creada.",
        )

    @extend_schema(summary="Revisar elegibilidad de una inscripción (RF8)")
    @action(detail=True, methods=["get"], permission_classes=[EsAdminUOrganizadorODelegado])
    def elegibilidad(self, request, pk=None):
        evaluacion = evaluar_inscripcion(self.get_object())
        evaluacion["aprobable"] = not evaluacion["bloqueantes"]
        return Response(evaluacion)

    @extend_schema(summary="Aprobar o rechazar una inscripción (RF6/RF8)")
    @action(
        detail=True,
        methods=["patch"],
        permission_classes=[EsAdminUOrganizador],
    )
    def validar(self, request, pk=None):
        inscripcion = self.get_object()
        if inscripcion.estado != Inscripcion.Estado.PENDIENTE:
            raise ValidationError(
                {"estado": "Solo se pueden validar inscripciones pendientes."}
            )
        nuevo_estado = request.data.get("estado")
        if nuevo_estado not in (
            Inscripcion.Estado.APROBADA,
            Inscripcion.Estado.RECHAZADA,
        ):
            raise ValidationError(
                {"estado": "El estado debe ser APROBADA o RECHAZADA."}
            )
        observaciones = (request.data.get("observaciones") or "").strip()
        advertencias = []
        if nuevo_estado == Inscripcion.Estado.RECHAZADA and not observaciones:
            raise ValidationError({"observaciones": "Indica el motivo del rechazo."})
        if (
            nuevo_estado == Inscripcion.Estado.APROBADA
            and inscripcion.campeonato.estado != Campeonato.Estado.INSCRIPCIONES
        ):
            raise ValidationError({
                "estado": "Las inscripciones de este campeonato no están abiertas: "
                          "no se pueden aprobar equipos nuevos."
            })
        if nuevo_estado == Inscripcion.Estado.APROBADA:
            evaluacion = evaluar_inscripcion(inscripcion)
            advertencias = evaluacion["advertencias"]
            if evaluacion["bloqueantes"]:
                registrar(
                    Bitacora.Accion.EDITAR,
                    request=request,
                    modulo="inscripcion",
                    objeto_id=inscripcion.pk,
                    descripcion="Aprobación de inscripción rechazada por elegibilidad.",
                    detalle={"motivos": evaluacion["bloqueantes"]},
                    resultado=Bitacora.Resultado.ERROR,
                )
                raise ValidationError({
                    "estado": "La inscripción no cumple los requisitos de elegibilidad.",
                    "motivos": evaluacion["bloqueantes"],
                })
        inscripcion.estado = nuevo_estado
        inscripcion.validado_por = request.user
        inscripcion.fecha_validacion = timezone.now()
        if observaciones:
            inscripcion.observaciones = observaciones
        inscripcion.save(
            update_fields=[
                "estado",
                "validado_por",
                "fecha_validacion",
                "observaciones",
            ]
        )
        registrar(
            Bitacora.Accion.EDITAR,
            request=request,
            modulo="inscripcion",
            objeto_id=inscripcion.pk,
            descripcion="Solicitud de inscripción validada.",
            detalle={"estado": nuevo_estado},
        )
        aprobada = nuevo_estado == Inscripcion.Estado.APROBADA
        resolucion = "aprobada" if aprobada else "rechazada"
        equipo = inscripcion.equipo
        notificar_usuarios(
            [equipo.delegado],
            f"Inscripción {resolucion}",
            f"La inscripción del equipo {equipo.nombre} en "
            f"{inscripcion.campeonato.nombre} fue {resolucion}."
            + (f" Observaciones: {observaciones}" if observaciones else ""),
        )
        datos = InscripcionSerializer(inscripcion).data
        datos["advertencias"] = advertencias
        return Response(datos)


@extend_schema(tags=["equipos"])
class FichaJugadorViewSet(viewsets.ModelViewSet):
    """CU06 — Ficha de jugadores por equipo."""
    queryset = FichaJugador.objects.filter(estado="ACTIVO").select_related(
        "equipo", "usuario"
    )
    serializer_class   = FichaJugadorSerializer
    filterset_fields   = ["equipo", "posicion"]
    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [EsAdminODelegadoDeSuFacultad()]
        return [EsAdminUOrganizadorODelegado()]

    def get_queryset(self):
        queryset = super().get_queryset()
        if es_delegado(self.request.user):
            return queryset.filter(equipo__facultad_id=self.request.user.facultad_id)
        return queryset

    def perform_create(self, serializer):
        ficha = serializer.save()
        registrar(
            Bitacora.Accion.CREAR,
            request=self.request,
            modulo="ficha_jugador",
            objeto_id=ficha.pk,
            descripcion="Ficha de jugador creada.",
        )

    def perform_update(self, serializer):
        ficha = serializer.save()
        registrar(
            Bitacora.Accion.EDITAR,
            request=self.request,
            modulo="ficha_jugador",
            objeto_id=ficha.pk,
            descripcion="Ficha de jugador actualizada.",
        )

    def perform_destroy(self, instance):
        registrar(
            Bitacora.Accion.ELIMINAR,
            request=self.request,
            modulo="ficha_jugador",
            objeto_id=instance.pk,
            descripcion="Ficha de jugador eliminada.",
        )
        instance.delete()
