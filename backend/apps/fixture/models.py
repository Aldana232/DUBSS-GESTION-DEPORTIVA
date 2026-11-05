"""
apps/fixture/models.py
CU08, CU10, CU11, CU12, CU13.
Modelos: Partido, Resultado, Incidencia, TablaPosiciones.
"""
from datetime import timedelta

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField
from django.contrib.postgres.fields.ranges import RangeOperators
from django.db import models
from django.db.models import F, Func, Q
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from apps.deportes.models import Campeonato, Equipo, Inscripcion, FichaJugador
from apps.instalaciones.models import Cancha


class Partido(models.Model):
    """CU08 / CU10 — Partido generado por el fixture."""

    class Estado(models.TextChoices):
        PROGRAMADO  = "PROGRAMADO",  "Programado"
        EN_CURSO    = "EN_CURSO",    "En curso"
        FINALIZADO  = "FINALIZADO",  "Finalizado"
        SUSPENDIDO  = "SUSPENDIDO",  "Suspendido"
        POSTERGADO  = "POSTERGADO",  "Postergado"
        WALKOVER    = "WALKOVER",    "Walkover (W.O.)"

    campeonato      = models.ForeignKey(Campeonato, on_delete=models.CASCADE,
                                        related_name="partidos")
    # Nulos solo en partidos "placeholder" de eliminación directa: el equipo
    # se completa cuando termina el partido de origen (ver resultados.avanzar_ganador).
    equipo_local    = models.ForeignKey(Equipo, on_delete=models.PROTECT,
                                        null=True, blank=True,
                                        related_name="partidos_local")
    equipo_visitante = models.ForeignKey(Equipo, on_delete=models.PROTECT,
                                         null=True, blank=True,
                                         related_name="partidos_visitante")
    ronda           = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="ronda de eliminación")
    partido_origen_local = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="siguiente_como_local")
    partido_origen_visitante = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="siguiente_como_visitante")
    cancha          = models.ForeignKey(Cancha, on_delete=models.SET_NULL,
                                        null=True, related_name="partidos")
    instalacion     = models.ForeignKey(
        "instalaciones.Instalacion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partidos",
    )
    fecha_hora      = models.DateTimeField(verbose_name="fecha y hora del partido")
    jornada         = models.PositiveSmallIntegerField(default=1,
                                                        verbose_name="jornada / fecha")
    fase            = models.CharField(max_length=50, default="Fase de grupos",
                                       verbose_name="fase del campeonato")
    estado          = models.CharField(max_length=15, choices=Estado.choices,
                                       default=Estado.PROGRAMADO)
    duracion_min    = models.PositiveSmallIntegerField(default=90)
    fecha_hora_fin  = models.DateTimeField()
    arbitro         = models.ForeignKey("users.Usuario", on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name="partidos_arbitrados")
    generado_por_ml = models.BooleanField(default=False,
                                          verbose_name="generado por ML")
    observaciones   = models.TextField(blank=True)
    creado_en       = models.DateTimeField(auto_now_add=True)
    actualizado_en  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Partido"
        verbose_name_plural = "Partidos"
        ordering            = ["fecha_hora"]
        constraints = [
            models.CheckConstraint(
                check=~Q(equipo_local=F("equipo_visitante")),
                name="partido_equipos_distintos",
            ),
            models.CheckConstraint(
                check=Q(duracion_min__gt=0),
                name="partido_duracion_positiva",
            ),
            models.CheckConstraint(
                check=Q(fecha_hora_fin__gt=F("fecha_hora")),
                name="partido_fin_despues_inicio",
            ),
            models.UniqueConstraint(
                fields=["campeonato", "equipo_local", "equipo_visitante", "jornada"],
                name="partido_campeonato_equipos_jornada_uniq",
            ),
            ExclusionConstraint(
                name="partido_cancha_sin_solapamiento",
                expressions=[
                    ("cancha", RangeOperators.EQUAL),
                    (
                        Func(
                            F("fecha_hora"),
                            F("fecha_hora_fin"),
                            function="TSTZRANGE",
                            output_field=DateTimeRangeField(),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                condition=Q(cancha__isnull=False),
            ),
        ]

    def __str__(self):
        local = self.equipo_local or "Por definir"
        visitante = self.equipo_visitante or "Por definir"
        return f"{local} vs {visitante} | {self.fecha_hora:%d/%m/%Y %H:%M}"

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        campos_actualizados = (
            set(update_fields) if update_fields is not None else None
        )
        if self.cancha_id and (
            self._state.adding
            or update_fields is None
            or {"cancha", "instalacion"} & set(update_fields)
        ):
            instalacion_id = Cancha.objects.values_list(
                "instalacion_id",
                flat=True,
            ).get(pk=self.cancha_id)
            if self.instalacion_id not in (None, instalacion_id):
                raise ValidationError(
                    "La instalación del partido debe coincidir con la de la cancha."
                )
            self.instalacion_id = instalacion_id
            if campos_actualizados is not None:
                campos_actualizados.add("instalacion")

        if self.fecha_hora is not None and self.duracion_min is not None:
            self.fecha_hora = self._meta.get_field("fecha_hora").to_python(
                self.fecha_hora
            )
            self.fecha_hora_fin = self.fecha_hora + timedelta(minutes=self.duracion_min)
            if campos_actualizados is not None and {
                "fecha_hora",
                "duracion_min",
            } & campos_actualizados:
                campos_actualizados.add("fecha_hora_fin")
        if campos_actualizados is not None:
            kwargs["update_fields"] = campos_actualizados
        super().save(*args, **kwargs)

    def clean(self):
        if self.equipo_local_id and self.equipo_local_id == self.equipo_visitante_id:
            raise ValidationError("El equipo local y visitante no pueden ser el mismo.")
        for equipo in (self.equipo_local, self.equipo_visitante):
            if equipo is None:
                continue
            inscrito = Inscripcion.objects.filter(
                campeonato=self.campeonato,
                equipo=equipo,
                estado=Inscripcion.Estado.APROBADA,
            ).exists()
            if not inscrito:
                raise ValidationError(
                    "Ambos equipos deben tener inscripción aprobada en el campeonato."
                )


class Resultado(models.Model):
    """CU11 — Resultado oficial de un partido."""

    partido         = models.OneToOneField(Partido, on_delete=models.CASCADE,
                                           related_name="resultado")
    goles_local     = models.PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0)])
    goles_visitante = models.PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0)])
    penales_local     = models.PositiveSmallIntegerField(null=True, blank=True)
    penales_visitante = models.PositiveSmallIntegerField(null=True, blank=True)
    walkover        = models.BooleanField(
        default=False, verbose_name="resultado administrativo (W.O.)")
    registrado_por  = models.ForeignKey("users.Usuario", on_delete=models.SET_NULL,
                                        null=True, related_name="resultados_registrados")
    registrado_en   = models.DateTimeField(auto_now_add=True)
    verificado      = models.BooleanField(default=False, verbose_name="verificado por admin")
    observaciones   = models.TextField(blank=True)

    class Meta:
        verbose_name        = "Resultado"
        verbose_name_plural = "Resultados"
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(penales_local__isnull=True, penales_visitante__isnull=True)
                    | Q(penales_local__isnull=False, penales_visitante__isnull=False)
                ),
                name="resultado_penales_completos",
            ),
        ]

    def __str__(self):
        return (
            f"{self.partido.equipo_local} {self.goles_local} - "
            f"{self.goles_visitante} {self.partido.equipo_visitante}"
        )

    @property
    def ganador(self):
        """Ganador del partido; si hay empate decide la tanda de penales."""
        if self.goles_local > self.goles_visitante:
            return self.partido.equipo_local
        if self.goles_visitante > self.goles_local:
            return self.partido.equipo_visitante
        if self.penales_local is not None and self.penales_local != self.penales_visitante:
            if self.penales_local > self.penales_visitante:
                return self.partido.equipo_local
            return self.partido.equipo_visitante
        return None  # Empate

    @property
    def es_empate(self):
        return self.goles_local == self.goles_visitante


class Incidencia(models.Model):
    """CU12 — Incidencias durante un partido (tarjetas, lesiones, etc.)."""

    class Tipo(models.TextChoices):
        GOL             = "GOL",             "Gol"
        TARJETA_AMARILLA = "TARJETA_AMARILLA", "Tarjeta amarilla"
        TARJETA_ROJA    = "TARJETA_ROJA",    "Tarjeta roja"
        LESION          = "LESION",          "Lesión"
        SUSTITUCION     = "SUSTITUCION",     "Sustitución"
        OTRO            = "OTRO",            "Otro"

    partido    = models.ForeignKey(Partido, on_delete=models.CASCADE,
                                   related_name="incidencias")
    tipo       = models.CharField(max_length=20, choices=Tipo.choices)
    jugador    = models.ForeignKey(FichaJugador, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="incidencias")
    minuto     = models.PositiveSmallIntegerField(null=True, blank=True,
                                                   verbose_name="minuto del partido")
    descripcion = models.TextField(blank=True)
    registrado_por = models.ForeignKey("users.Usuario", on_delete=models.SET_NULL,
                                       null=True, related_name="incidencias_registradas")
    registrado_en  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Incidencia"
        verbose_name_plural = "Incidencias"
        ordering            = ["partido", "minuto"]

    def __str__(self):
        return f"{self.tipo} — {self.partido} min. {self.minuto}"


class TablaPosiciones(models.Model):
    """
    CU13 — Tabla de posiciones calculada por campeonato y equipo.
    Desnormalización controlada: se reconstruye desde los Resultado con
    fixture.services.tabla.recalcular (idempotente).
    """
    campeonato = models.ForeignKey(Campeonato, on_delete=models.CASCADE,
                                   related_name="tabla_posiciones")
    equipo     = models.ForeignKey(Equipo, on_delete=models.CASCADE,
                                   related_name="posicion_en_tabla")
    pj  = models.PositiveSmallIntegerField(default=0, verbose_name="partidos jugados")
    pg  = models.PositiveSmallIntegerField(default=0, verbose_name="partidos ganados")
    pe  = models.PositiveSmallIntegerField(default=0, verbose_name="partidos empatados")
    pp  = models.PositiveSmallIntegerField(default=0, verbose_name="partidos perdidos")
    gf  = models.PositiveSmallIntegerField(default=0, verbose_name="goles a favor")
    gc  = models.PositiveSmallIntegerField(default=0, verbose_name="goles en contra")
    puntos = models.SmallIntegerField(default=0)
    posicion = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name        = "Tabla de Posiciones"
        verbose_name_plural = "Tabla de Posiciones"
        unique_together     = ["campeonato", "equipo"]
        ordering            = ["posicion", "-puntos", "-gf"]

    def __str__(self):
        return f"{self.equipo} — {self.puntos} pts"

    @property
    def diferencia_goles(self):
        return self.gf - self.gc


class PosicionHistorial(models.Model):
    """RF13 — Foto de la tabla de posiciones al cerrar cada jornada."""
    campeonato = models.ForeignKey(Campeonato, on_delete=models.CASCADE,
                                   related_name="historial_posiciones")
    jornada    = models.PositiveSmallIntegerField()
    equipo     = models.ForeignKey(Equipo, on_delete=models.CASCADE,
                                   related_name="historial_posiciones")
    posicion   = models.PositiveSmallIntegerField()
    puntos     = models.SmallIntegerField(default=0)
    pj = models.PositiveSmallIntegerField(default=0)
    gf = models.PositiveSmallIntegerField(default=0)
    gc = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name        = "Historial de posiciones"
        verbose_name_plural = "Historial de posiciones"
        ordering            = ["campeonato", "jornada", "posicion"]
        constraints = [
            models.UniqueConstraint(
                fields=["campeonato", "jornada", "equipo"],
                name="historial_unico_jornada_equipo",
            ),
        ]

    def __str__(self):
        return f"J{self.jornada} #{self.posicion} {self.equipo}"


class OperacionIdempotente(models.Model):
    """
    F7-06 — Registro de operaciones de escritura ya aplicadas, identificadas por la cabecera `Idempotency-Key`.

    El celular genera una clave por acción y la reenvía tal cual si no sabe si llegó (se cayó la señal justo
    después de enviar). El servidor reconoce la clave, no vuelve a ejecutar y devuelve la respuesta guardada.
    Solo se guardan las operaciones EXITOSAS: el registro nace y muere en la misma transacción que la operación.
    """
    usuario  = models.ForeignKey("users.Usuario", on_delete=models.CASCADE, related_name="operaciones_idempotentes")
    clave    = models.CharField(max_length=64)
    metodo   = models.CharField(max_length=8)
    ruta     = models.CharField(max_length=200)
    huella   = models.CharField(max_length=64, help_text="SHA-256 del método, la ruta y el cuerpo.")
    codigo   = models.PositiveSmallIntegerField(null=True, blank=True)
    respuesta = models.JSONField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Operación idempotente"
        verbose_name_plural = "Operaciones idempotentes"
        constraints = [models.UniqueConstraint(fields=["usuario", "clave"], name="operacion_idempotente_usuario_clave_uniq")]
