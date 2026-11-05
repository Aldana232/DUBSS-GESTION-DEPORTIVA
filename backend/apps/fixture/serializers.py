from django.conf import settings
from rest_framework import serializers

from apps.deportes.models import Campeonato, Inscripcion
from apps.deportes.serializers import EquipoResumenSerializer
from apps.instalaciones.serializers import CanchaSerializer
from apps.users.serializers import UsuarioResumenSerializer
from .models import Partido, Resultado, Incidencia, TablaPosiciones
from .services import sanciones
from .services.programacion import detectar_conflictos, ConflictoProgramacion


class ResultadoSerializer(serializers.ModelSerializer):
    """
    RF12. Contexto: `partido` (obligatorio al escribir) y `corregir` (bool).
    Campos de solo escritura: `ganador_walkover` (LOCAL|VISITANTE) y `motivo`
    (obligatorio al corregir; se guarda en la bitácora).
    """
    ganador       = serializers.SerializerMethodField()
    es_empate     = serializers.BooleanField(read_only=True)
    ganador_walkover = serializers.ChoiceField(
        choices=["LOCAL", "VISITANTE"], write_only=True, required=False)
    motivo = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model  = Resultado
        fields = ["id", "partido", "goles_local", "goles_visitante",
                  "penales_local", "penales_visitante", "walkover",
                  "ganador_walkover", "motivo",
                  "ganador", "es_empate", "registrado_por",
                  "registrado_en", "verificado", "observaciones"]
        read_only_fields = ["id", "partido", "registrado_por", "registrado_en"]

    def _valor(self, attrs, campo, defecto):
        if campo in attrs:
            return attrs[campo]
        if self.instance is not None:
            return getattr(self.instance, campo)
        return defecto

    def validate(self, attrs):
        partido = self.context.get("partido")
        if partido is None:
            return attrs

        if partido.equipo_local_id is None or partido.equipo_visitante_id is None:
            raise serializers.ValidationError(
                "El partido aún no tiene los dos equipos definidos."
            )

        ganador_wo = attrs.pop("ganador_walkover", None)
        motivo = (attrs.pop("motivo", "") or "").strip()
        if self.context.get("corregir") and not motivo:
            raise serializers.ValidationError(
                {"motivo": "Indica el motivo de la corrección."}
            )
        self.motivo = motivo

        if self._valor(attrs, "walkover", False):
            if "goles_local" not in attrs or "goles_visitante" not in attrs:
                if ganador_wo is None:
                    raise serializers.ValidationError(
                        {"ganador_walkover": "Indica quién gana por W.O. (LOCAL o VISITANTE)."}
                    )
                gana = settings.WALKOVER_GOLES_GANADOR
                attrs["goles_local"] = gana if ganador_wo == "LOCAL" else 0
                attrs["goles_visitante"] = gana if ganador_wo == "VISITANTE" else 0
            attrs["penales_local"] = attrs["penales_visitante"] = None
            if attrs["goles_local"] == attrs["goles_visitante"]:
                raise serializers.ValidationError(
                    "Un resultado por W.O. necesita un ganador (el marcador no puede empatar)."
                )
            return attrs

        goles_local = self._valor(attrs, "goles_local", 0)
        goles_visitante = self._valor(attrs, "goles_visitante", 0)
        eliminacion = partido.campeonato.formato == Campeonato.Formato.ELIMINACION
        if goles_local != goles_visitante and "penales_local" not in attrs \
                and "penales_visitante" not in attrs:
            attrs["penales_local"] = attrs["penales_visitante"] = None
        penales_local = self._valor(attrs, "penales_local", None)
        penales_visitante = self._valor(attrs, "penales_visitante", None)
        if (penales_local is None) != (penales_visitante is None):
            raise serializers.ValidationError("Indica los penales de ambos equipos.")
        if penales_local is not None:
            if not eliminacion:
                raise serializers.ValidationError(
                    "Los penales solo aplican en eliminación directa."
                )
            if goles_local != goles_visitante:
                raise serializers.ValidationError(
                    "Los penales solo se registran cuando el marcador termina empatado."
                )
            if penales_local == penales_visitante:
                raise serializers.ValidationError(
                    "La tanda de penales no puede terminar empatada."
                )
        elif eliminacion and goles_local == goles_visitante:
            raise serializers.ValidationError(
                "En eliminación directa el empate se define por penales: "
                "indica penales_local y penales_visitante."
            )

        goles = list(
            partido.incidencias.filter(tipo=Incidencia.Tipo.GOL).select_related(
                "jugador__equipo"
            )
        )
        if not goles:
            return attrs

        goles_por_equipo = {
            partido.equipo_local_id: 0,
            partido.equipo_visitante_id: 0,
        }
        for incidencia in goles:
            if (
                incidencia.jugador_id is None
                or incidencia.jugador.equipo_id not in goles_por_equipo
            ):
                raise serializers.ValidationError(
                    "Cada incidencia de gol debe identificar un jugador de uno de "
                    "los equipos del partido."
                )
            goles_por_equipo[incidencia.jugador.equipo_id] += 1

        marcador = {
            partido.equipo_local_id: goles_local,
            partido.equipo_visitante_id: goles_visitante,
        }
        if goles_por_equipo != marcador:
            raise serializers.ValidationError(
                "El marcador debe coincidir con las incidencias de gol registradas."
            )
        return attrs

    def get_ganador(self, obj):
        g = obj.ganador
        return {"id": g.id, "nombre": g.nombre} if g else None


class IncidenciaSerializer(serializers.ModelSerializer):
    """RF14. Contexto: `partido` (el partido de la URL)."""
    jugador_nombre = serializers.SerializerMethodField()
    equipo_id = serializers.IntegerField(source="jugador.equipo_id", read_only=True, default=None)

    class Meta:
        model  = Incidencia
        fields = ["id", "partido", "tipo", "jugador", "jugador_nombre", "equipo_id", "minuto",
                  "descripcion", "registrado_por", "registrado_en"]
        read_only_fields = ["id", "partido", "registrado_por", "registrado_en"]

    def get_jugador_nombre(self, obj) -> str | None:
        return f"{obj.jugador.nombre} {obj.jugador.apellido}".strip() if obj.jugador_id else None

    def validate(self, attrs):
        partido = self.context.get("partido")
        if partido is None:
            return attrs
        if partido.equipo_local_id is None or partido.equipo_visitante_id is None:
            raise serializers.ValidationError(
                "El partido aún no tiene los dos equipos definidos."
            )
        if partido.estado == Partido.Estado.WALKOVER:
            raise serializers.ValidationError(
                "No se registran incidencias en un partido resuelto por W.O."
            )
        tipo = attrs.get("tipo")
        jugador = attrs.get("jugador")
        if jugador is None:
            if tipo in sanciones.TIPOS_CON_JUGADOR:
                raise serializers.ValidationError(
                    {"jugador": "Indica el jugador para este tipo de incidencia."}
                )
            return attrs
        if jugador.equipo_id not in (partido.equipo_local_id, partido.equipo_visitante_id):
            raise serializers.ValidationError(
                {"jugador": "El jugador debe pertenecer al equipo local o visitante del partido."}
            )
        if (
            jugador.partidos_sancion_restantes > 0
            and not sanciones.sancion_proviene_del_partido(jugador, partido)
        ):
            raise serializers.ValidationError({
                "jugador": f"El jugador está sancionado ({jugador.partidos_sancion_restantes} "
                           "partido(s) pendiente(s)) y no puede participar."
            })
        return attrs

    def create(self, validated_data):
        validated_data["registrado_por"] = self.context["request"].user
        return super().create(validated_data)


class PartidoSerializer(serializers.ModelSerializer):
    equipo_local_detalle    = EquipoResumenSerializer(source="equipo_local",    read_only=True)
    equipo_visitante_detalle = EquipoResumenSerializer(source="equipo_visitante", read_only=True)
    cancha_detalle          = CanchaSerializer(source="cancha",                 read_only=True)
    arbitro_detalle         = UsuarioResumenSerializer(source="arbitro",        read_only=True)
    resultado               = ResultadoSerializer(read_only=True)
    incidencias             = IncidenciaSerializer(many=True, read_only=True)

    ESTADOS_EDITABLES = (
        Partido.Estado.PROGRAMADO, Partido.Estado.EN_CURSO,
        Partido.Estado.SUSPENDIDO, Partido.Estado.POSTERGADO,
    )

    class Meta:
        model  = Partido
        fields = [
            "id", "campeonato", "jornada", "fase", "ronda",
            "equipo_local",     "equipo_local_detalle",
            "equipo_visitante", "equipo_visitante_detalle",
            "partido_origen_local", "partido_origen_visitante",
            "cancha", "cancha_detalle", "instalacion",
            "fecha_hora", "duracion_min", "fecha_hora_fin",
            "estado", "generado_por_ml",
            "arbitro",    "arbitro_detalle",
            "resultado", "incidencias",
            "observaciones", "creado_en", "actualizado_en",
        ]
        read_only_fields = [
            "id", "fecha_hora_fin", "creado_en", "actualizado_en",
            "ronda", "partido_origen_local", "partido_origen_visitante",
            "generado_por_ml",
        ]

    def validate(self, attrs):
        instancia = self.instance
        valor = lambda campo: attrs.get(campo, getattr(instancia, campo, None))  # noqa: E731

        if instancia is not None:
            for campo, nombre in (
                ("campeonato", "el campeonato"),
                ("equipo_local", "el equipo local"),
                ("equipo_visitante", "el equipo visitante"),
            ):
                if campo in attrs and attrs[campo] != getattr(instancia, campo):
                    raise serializers.ValidationError(
                        {campo: f"No se puede cambiar {nombre} de un partido; "
                                "elimínalo y crea uno nuevo."}
                    )

        if "estado" in attrs and attrs["estado"] not in self.ESTADOS_EDITABLES \
                and (instancia is None or attrs["estado"] != instancia.estado):
            raise serializers.ValidationError({
                "estado": "FINALIZADO y WALKOVER se asignan al registrar el resultado."
            })
        if instancia is not None and instancia.estado in (
            Partido.Estado.FINALIZADO, Partido.Estado.WALKOVER
        ):
            raise serializers.ValidationError(
                "El partido ya tiene resultado; corrige el resultado en lugar de editar el partido."
            )

        local, visitante = valor("equipo_local"), valor("equipo_visitante")
        campeonato = valor("campeonato")
        if instancia is None:
            if local is None or visitante is None:
                raise serializers.ValidationError(
                    "Un partido manual necesita equipo local y visitante."
                )
            if local == visitante:
                raise serializers.ValidationError(
                    "El equipo local y visitante no pueden ser el mismo."
                )
            if campeonato.estado in (Campeonato.Estado.FINALIZADO, Campeonato.Estado.CANCELADO):
                raise serializers.ValidationError(
                    "No se pueden programar partidos en un campeonato finalizado o cancelado."
                )
            for equipo in (local, visitante):
                if not Inscripcion.objects.filter(
                    campeonato=campeonato, equipo=equipo,
                    estado=Inscripcion.Estado.APROBADA,
                ).exists():
                    raise serializers.ValidationError(
                        f"El equipo {equipo.nombre} no tiene inscripción aprobada "
                        "en el campeonato."
                    )

        cancha = valor("cancha")
        if cancha is not None:
            instalacion = attrs.get("instalacion", getattr(instancia, "instalacion", None))
            if instalacion is None or ("cancha" in attrs and "instalacion" not in attrs):
                attrs["instalacion"] = cancha.instalacion
            elif instalacion.pk != cancha.instalacion_id:
                raise serializers.ValidationError(
                    {"instalacion": "Debe coincidir con la instalación de la cancha."}
                )

        cambia_horario = instancia is None or any(
            campo in attrs and attrs[campo] != getattr(instancia, campo)
            for campo in ("fecha_hora", "cancha", "duracion_min")
        )
        if cambia_horario and valor("fecha_hora") is not None:
            conflictos = detectar_conflictos(
                cancha=cancha,
                fecha_hora=valor("fecha_hora"),
                duracion_min=valor("duracion_min") or 90,
                equipo_local=local,
                equipo_visitante=visitante,
                partido_id=getattr(instancia, "pk", None),
            )
            if conflictos:
                raise ConflictoProgramacion(conflictos)
        return attrs


class PartidoResumenSerializer(serializers.ModelSerializer):
    """Compacto para calendarios y listados."""
    local    = serializers.CharField(source="equipo_local.nombre", default="Por definir")
    visitante = serializers.CharField(source="equipo_visitante.nombre", default="Por definir")
    cancha   = serializers.CharField(source="cancha.nombre", default="")
    goles_local = serializers.IntegerField(source="resultado.goles_local", default=None, read_only=True)
    goles_visitante = serializers.IntegerField(source="resultado.goles_visitante", default=None, read_only=True)

    class Meta:
        model  = Partido
        fields = ["id", "jornada", "fase", "ronda", "local", "visitante",
                  "cancha", "instalacion", "fecha_hora", "duracion_min",
                  "fecha_hora_fin", "estado", "generado_por_ml", "goles_local", "goles_visitante"]
        read_only_fields = ["fecha_hora_fin"]


class TablaPosicionesSerializer(serializers.ModelSerializer):
    equipo_detalle     = EquipoResumenSerializer(source="equipo", read_only=True)
    diferencia_goles   = serializers.IntegerField(read_only=True)

    class Meta:
        model  = TablaPosiciones
        fields = ["id", "campeonato", "equipo", "equipo_detalle", "posicion",
                  "pj", "pg", "pe", "pp", "gf", "gc",
                  "diferencia_goles", "puntos"]
        read_only_fields = fields
