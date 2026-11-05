"""
apps/deportes/serializers.py
Serializers para Deporte, Categoria, Campeonato, Equipo, FichaJugador.
"""
from django.utils import timezone
from rest_framework import serializers
from apps.users.serializers import UsuarioResumenSerializer
from apps.users.roles import es_delegado
from .models import (
    Facultad, RestriccionHorarioFacultad, Deporte, Categoria, Campeonato,
    Equipo, Inscripcion, FichaJugador,
)
from .services import transiciones_permitidas


class FacultadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facultad
        fields = ["id", "nombre", "sigla"]
        read_only_fields = ["id"]


class RestriccionHorarioFacultadSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestriccionHorarioFacultad
        fields = ["id", "facultad", "dia_semana", "hora_inicio", "hora_fin", "motivo"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        inicio = attrs.get("hora_inicio", getattr(self.instance, "hora_inicio", None))
        fin = attrs.get("hora_fin", getattr(self.instance, "hora_fin", None))
        if inicio is not None and fin is not None and fin <= inicio:
            raise serializers.ValidationError(
                {"hora_fin": "La hora de fin debe ser posterior al inicio."}
            )
        return attrs


class DeporteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Deporte
        fields = [
            "id", "nombre", "descripcion", "cantidad_jugadores",
            "imagen", "activo", "creado_en",
        ]
        read_only_fields = ["id", "creado_en"]


class CategoriaSerializer(serializers.ModelSerializer):
    deporte_nombre = serializers.CharField(source="deporte.nombre", read_only=True)

    class Meta:
        model  = Categoria
        fields = [
            "id", "deporte", "deporte_nombre", "nombre", "genero",
            "rango_edad", "descripcion", "activa",
        ]
        read_only_fields = ["id"]


class CampeonatoSerializer(serializers.ModelSerializer):
    deporte = serializers.IntegerField(source="categoria.deporte_id", read_only=True)
    deporte_detalle  = DeporteSerializer(source="categoria.deporte", read_only=True)
    categoria_detalle = CategoriaSerializer(source="categoria", read_only=True)
    creado_por_detalle = UsuarioResumenSerializer(source="creado_por", read_only=True)
    total_equipos    = serializers.SerializerMethodField()
    transiciones_permitidas = serializers.SerializerMethodField()

    class Meta:
        model  = Campeonato
        fields = [
            "id", "nombre",
            "deporte", "deporte_detalle",
            "categoria", "categoria_detalle",
            "estado", "transiciones_permitidas", "formato",
            "fecha_inicio", "fecha_fin", "max_equipos", "total_equipos",
            "min_jugadores", "max_jugadores", "fecha_cierre_inscripcion",
            "puntos_victoria", "puntos_empate", "puntos_derrota",
            "descripcion", "imagen_banner",
            "creado_por", "creado_por_detalle",
            "creado_en", "actualizado_en",
        ]
        # El estado solo cambia con PATCH /campeonatos/{id}/estado/ (máquina de estados).
        read_only_fields = ["id", "estado", "creado_en", "actualizado_en", "creado_por"]

    def get_transiciones_permitidas(self, obj):
        return transiciones_permitidas(obj.estado)

    def get_total_equipos(self, obj):
        return obj.inscripciones.filter(
            estado=Inscripcion.Estado.APROBADA,
            equipo__estado="ACTIVO",
        ).count()

    def create(self, validated_data):
        validated_data["creado_por"] = self.context["request"].user
        return super().create(validated_data)

    def validate(self, attrs):
        fecha_inicio = attrs.get("fecha_inicio", getattr(self.instance, "fecha_inicio", None))
        fecha_fin = attrs.get("fecha_fin", getattr(self.instance, "fecha_fin", None))
        min_jugadores = attrs.get(
            "min_jugadores",
            getattr(self.instance, "min_jugadores", 0),
        )
        max_jugadores = attrs.get(
            "max_jugadores",
            getattr(self.instance, "max_jugadores", 99),
        )
        fecha_cierre = attrs.get(
            "fecha_cierre_inscripcion",
            getattr(self.instance, "fecha_cierre_inscripcion", None),
        )
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError(
                {"fecha_fin": "La fecha de fin no puede ser anterior a la fecha de inicio."}
            )
        if min_jugadores > max_jugadores:
            raise serializers.ValidationError(
                {"min_jugadores": "No puede superar el máximo de jugadores."}
            )
        if fecha_cierre and fecha_inicio and fecha_cierre.date() >= fecha_inicio:
            raise serializers.ValidationError(
                {"fecha_cierre_inscripcion": "El cierre debe ser anterior al inicio del campeonato."}
            )
        categoria = attrs.get("categoria", getattr(self.instance, "categoria", None))
        if categoria is not None and not categoria.activa:
            raise serializers.ValidationError(
                {"categoria": "La categoría seleccionada no está activa."}
            )
        max_equipos = attrs.get("max_equipos", getattr(self.instance, "max_equipos", 8))
        if max_equipos < 2:
            raise serializers.ValidationError(
                {"max_equipos": "Un campeonato necesita al menos 2 equipos."}
            )
        if self.instance is not None:
            aprobadas = self.instance.inscripciones.filter(estado=Inscripcion.Estado.APROBADA).count()
            if max_equipos < aprobadas:
                raise serializers.ValidationError(
                    {"max_equipos": f"Ya hay {aprobadas} equipos aprobados: el cupo no puede ser menor."}
                )
            if self.instance.partidos.exists():
                for campo, nombre in (("formato", "el formato"), ("categoria", "la categoría")):
                    if campo in attrs and attrs[campo] != getattr(self.instance, campo):
                        raise serializers.ValidationError(
                            {campo: f"No se puede cambiar {nombre} con un fixture generado."}
                        )
        return attrs


class FichaJugadorSerializer(serializers.ModelSerializer):
    usuario_detalle = UsuarioResumenSerializer(source="usuario", read_only=True)

    class Meta:
        model  = FichaJugador
        fields = [
            "id", "equipo", "usuario", "usuario_detalle", "nombre", "apellido",
            "carnet", "registro", "posicion", "numero_camiseta", "estado",
            "creado_en", "partidos_sancion_restantes", "sancion_origen",
        ]
        read_only_fields = [
            "id", "creado_en", "partidos_sancion_restantes", "sancion_origen",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        if request is not None and es_delegado(request.user):
            equipo = attrs.get("equipo", getattr(self.instance, "equipo", None))
            if equipo is None or equipo.facultad_id != request.user.facultad_id:
                raise serializers.ValidationError(
                    {"equipo": "Solo puedes gestionar fichas de equipos de tu facultad."}
                )
        return attrs


class EquipoSerializer(serializers.ModelSerializer):
    delegado_detalle  = UsuarioResumenSerializer(source="delegado", read_only=True)
    jugadores         = FichaJugadorSerializer(many=True, read_only=True)
    cantidad_jugadores = serializers.IntegerField(read_only=True)
    facultad_nombre = serializers.CharField(source="facultad.nombre", read_only=True)
    color_principal = serializers.CharField(source="color", read_only=True)

    class Meta:
        model  = Equipo
        fields = [
            "id", "nombre", "facultad", "facultad_nombre", "color", "color_principal",
            "logo", "estado", "creado_en", "delegado", "delegado_detalle",
            "jugadores", "cantidad_jugadores",
        ]
        read_only_fields = ["id", "creado_en"]

    def validate(self, attrs):
        request = self.context.get("request")
        delegado = attrs.get("delegado", getattr(self.instance, "delegado", None))
        facultad = attrs.get("facultad", getattr(self.instance, "facultad", None))
        if request is not None and es_delegado(request.user):
            facultad_solicitante = request.user.facultad
            if facultad_solicitante is None:
                raise serializers.ValidationError(
                    {"facultad": "Tu cuenta no tiene una facultad asignada."}
                )
            if facultad is not None and facultad.pk != facultad_solicitante.pk:
                raise serializers.ValidationError(
                    {"facultad": "Solo puedes gestionar equipos de tu facultad."}
                )
            attrs["facultad"] = facultad_solicitante
            if self.instance is None:
                attrs["delegado"] = request.user
            elif "delegado" in attrs and attrs["delegado"] != self.instance.delegado:
                raise serializers.ValidationError(
                    {"delegado": "No puedes cambiar el delegado responsable del equipo."}
                )
        if delegado is not None:
            if not es_delegado(delegado):
                raise serializers.ValidationError(
                    {"delegado": "El responsable debe tener el rol DELEGADO."}
                )
            if delegado.facultad_id != getattr(facultad, "pk", None):
                raise serializers.ValidationError(
                    {"delegado": "El delegado debe pertenecer a la facultad del equipo."}
                )
        return attrs


class EquipoResumenSerializer(serializers.ModelSerializer):
    """Serializer compacto para usar en fixture/partidos."""
    facultad = serializers.CharField(source="facultad.nombre", read_only=True)
    color_principal = serializers.CharField(source="color", read_only=True)

    class Meta:
        model  = Equipo
        fields = ["id", "nombre", "facultad", "logo", "color_principal"]


class InscripcionSerializer(serializers.ModelSerializer):
    equipo_detalle = EquipoResumenSerializer(source="equipo", read_only=True)
    campeonato_nombre = serializers.CharField(source="campeonato.nombre", read_only=True)

    class Meta:
        model = Inscripcion
        fields = [
            "id", "campeonato", "campeonato_nombre", "equipo", "equipo_detalle",
            "fecha_inscripcion", "estado", "validado_por", "fecha_validacion",
            "observaciones",
        ]
        read_only_fields = [
            "id", "fecha_inscripcion", "estado", "validado_por", "fecha_validacion",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        equipo = attrs.get("equipo", getattr(self.instance, "equipo", None))
        campeonato = attrs.get(
            "campeonato", getattr(self.instance, "campeonato", None)
        )
        if request is not None and es_delegado(request.user):
            if equipo is not None and equipo.facultad_id != request.user.facultad_id:
                raise serializers.ValidationError(
                    {"equipo": "Solo puedes inscribir equipos de tu facultad."}
                )
        if self.instance is None and campeonato is not None:
            if campeonato.estado != Campeonato.Estado.INSCRIPCIONES:
                raise serializers.ValidationError(
                    {"campeonato": "El campeonato no está recibiendo inscripciones."}
                )
            cierre = campeonato.fecha_cierre_inscripcion
            if cierre is not None and timezone.now() >= cierre:
                raise serializers.ValidationError(
                    {"campeonato": "El plazo de inscripción del campeonato ha cerrado."}
                )
            if equipo is not None and equipo.estado != "ACTIVO":
                raise serializers.ValidationError(
                    {"equipo": "El equipo no está activo."}
                )
        return attrs
