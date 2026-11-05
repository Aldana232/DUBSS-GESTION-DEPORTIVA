"""
apps/ml/models.py
CU14–CU16, CU18, CU20 — Predicciones ML y bitácora del sistema.
"""
from django.db import models
from apps.fixture.models import Partido


class PrediccionPartido(models.Model):
    """CU16 — Predicción de resultado de un partido generada por el modelo ML."""

    partido             = models.OneToOneField(Partido, on_delete=models.CASCADE,
                                               related_name="prediccion")
    prob_victoria_local = models.FloatField(verbose_name="prob. victoria local (0-1)")
    prob_empate         = models.FloatField(verbose_name="prob. empate (0-1)")
    prob_victoria_visit = models.FloatField(verbose_name="prob. victoria visitante (0-1)")
    goles_local_pred    = models.FloatField(verbose_name="goles local predichos")
    goles_visit_pred    = models.FloatField(verbose_name="goles visitante predichos")
    confianza           = models.FloatField(verbose_name="confianza del modelo (0-1)")
    datos_suficientes   = models.BooleanField(
        default=False, verbose_name="¿hay historial suficiente de ambos equipos?")
    modelo_version      = models.CharField(max_length=50, default="elo-base")
    generado_en         = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Predicción de Partido"
        verbose_name_plural = "Predicciones de Partidos"

    def __str__(self):
        return f"Predicción: {self.partido}"


class PrediccionAsistencia(models.Model):
    """CU20 — Predicción de asistencia de espectadores a un partido."""

    partido             = models.OneToOneField(Partido, on_delete=models.CASCADE,
                                               related_name="pred_asistencia")
    asistencia_predicha = models.PositiveIntegerField(verbose_name="asistencia predicha")
    rango_min           = models.PositiveIntegerField()
    rango_max           = models.PositiveIntegerField()
    factores            = models.JSONField(default=dict,
                                           verbose_name="factores considerados")
    generado_en         = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Predicción de Asistencia"
        verbose_name_plural = "Predicciones de Asistencia"


class RiesgoClimatico(models.Model):
    """CU15 — Pronóstico de riesgo climático para un partido."""

    class NivelRiesgo(models.TextChoices):
        BAJO   = "BAJO",   "Bajo"
        MEDIO  = "MEDIO",  "Medio"
        ALTO   = "ALTO",   "Alto"
        CRITICO = "CRITICO", "Crítico — considerar suspensión"
        SIN_DATOS = "SIN_DATOS", "Sin datos (pronóstico no disponible)"

    partido         = models.ForeignKey(Partido, on_delete=models.CASCADE,
                                        related_name="riesgos_climaticos")
    nivel_riesgo    = models.CharField(max_length=10, choices=NivelRiesgo.choices)
    temperatura     = models.FloatField(null=True, blank=True, verbose_name="temperatura (°C)")
    precipitacion   = models.FloatField(null=True, blank=True, verbose_name="precipitación (mm)")
    viento          = models.FloatField(null=True, blank=True, verbose_name="viento (km/h)")
    descripcion     = models.TextField(blank=True)
    recomendacion   = models.TextField(blank=True)
    fuente_api      = models.CharField(max_length=50, default="Open-Meteo")
    consultado_en   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Riesgo Climático"
        verbose_name_plural = "Riesgos Climáticos"
        ordering            = ["-consultado_en"]


class MuestraAsignacion(models.Model):
    """
    RF11 — Muestra del dataset del puntuador de asignaciones (Random Forest).

    Describe una asignación "partido -> instalación y horario" y su calidad.
    Los ids de equipos e instalación son enteros planos (NO llaves foráneas) por diseño
    del documento: la muestra debe sobrevivir aunque se borren los partidos.
    Ampliaciones sobre el DDL del Cap. 7: `origen`, `holgura_facultad_min` y `partido_id`.
    """

    class Calidad(models.TextChoices):
        BUENA = "BUENA", "Buena"
        MALA = "MALA", "Mala"

    class Origen(models.TextChoices):
        REGLAS = "REGLAS", "Reglas de arranque en frío"
        REAL = "REAL", "Partido real"

    equipo_local_id         = models.IntegerField()
    equipo_visitante_id     = models.IntegerField()
    instalacion_id          = models.IntegerField()
    franja_horaria          = models.PositiveSmallIntegerField(verbose_name="hora de inicio (0-23)")
    dia_semana              = models.PositiveSmallIntegerField(verbose_name="día (0=lunes)")
    dias_desde_ultimo_local = models.IntegerField()
    dias_desde_ultimo_visit = models.IntegerField()
    instalacion_disponible  = models.BooleanField()
    conflictos_horario      = models.PositiveSmallIntegerField()
    calidad                 = models.CharField(max_length=12, choices=Calidad.choices)
    creado_en               = models.DateTimeField(auto_now_add=True)
    # Ampliaciones
    origen                  = models.CharField(max_length=10, choices=Origen.choices,
                                               default=Origen.REGLAS)
    holgura_facultad_min    = models.PositiveSmallIntegerField(default=240)
    partido_id              = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name        = "Muestra de asignación"
        verbose_name_plural = "Muestras de asignación"
        constraints = [
            models.UniqueConstraint(
                fields=["partido_id"],
                condition=models.Q(partido_id__isnull=False),
                name="muestra_unica_por_partido",
            ),
        ]

    def __str__(self):
        return f"{self.origen} {self.calidad} h{self.franja_horaria} d{self.dia_semana}"


class ModeloML(models.Model):
    """
    Registro de los modelos entrenados (F6-01): qué se entrenó, con qué datos y cómo rindió.
    Solo un modelo por `nombre` está `activo`; es el que usa la inferencia.
    """

    nombre              = models.CharField(max_length=60, db_index=True)
    version             = models.CharField(max_length=60)
    metricas            = models.JSONField(default=dict)
    fecha_entrenamiento = models.DateTimeField(auto_now_add=True)
    hash_datos          = models.CharField(max_length=64, verbose_name="huella SHA-256 de los datos")
    ruta_artefacto      = models.CharField(max_length=255, blank=True)
    activo              = models.BooleanField(default=False)

    class Meta:
        verbose_name        = "Modelo de ML"
        verbose_name_plural = "Modelos de ML"
        ordering            = ["-fecha_entrenamiento"]
        constraints = [
            models.UniqueConstraint(fields=["nombre", "version"], name="modeloml_nombre_version_uniq"),
            models.UniqueConstraint(
                fields=["nombre"], condition=models.Q(activo=True), name="modeloml_un_activo_por_nombre"),
        ]

    def __str__(self):
        return f"{self.nombre} {self.version}{' (activo)' if self.activo else ''}"


class ResultadoAtipico(models.Model):
    """
    F7-08 — Marcador que el Isolation Forest considera raro Y que se puede explicar con estadísticas simples.
    Es una alerta para revisar (un error de tipeo, un 8-0 sospechoso), nunca una corrección automática.
    """
    partido = models.OneToOneField("fixture.Partido", on_delete=models.CASCADE, related_name="alerta_atipica")
    puntaje = models.FloatField(verbose_name="índice de anomalía (0-1, mayor = más raro)")
    motivo = models.CharField(max_length=300)
    detectado_en = models.DateTimeField(auto_now_add=True)
    revisado = models.BooleanField(default=False)
    revisado_por = models.ForeignKey("users.Usuario", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    revisado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Resultado atípico"
        verbose_name_plural = "Resultados atípicos"
        ordering = ["revisado", "-puntaje"]
