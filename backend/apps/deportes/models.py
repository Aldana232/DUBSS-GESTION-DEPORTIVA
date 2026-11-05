"""
apps/deportes/models.py
Modelos: Deporte, Categoria, Campeonato, Equipo, FichaJugador.
Cubre CU03, CU04, CU05, CU06, CU09.
"""
from django.db import models
from apps.users.models import Usuario


class Facultad(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    sigla = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Facultad"
        verbose_name_plural = "Facultades"

    def __str__(self):
        return self.nombre


class RestriccionHorarioFacultad(models.Model):
    class DiaSemana(models.IntegerChoices):
        LUNES = 0, "Lunes"
        MARTES = 1, "Martes"
        MIERCOLES = 2, "Miércoles"
        JUEVES = 3, "Jueves"
        VIERNES = 4, "Viernes"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"

    facultad = models.ForeignKey(
        Facultad,
        on_delete=models.CASCADE,
        related_name="restricciones_horario",
    )
    dia_semana = models.PositiveSmallIntegerField(choices=DiaSemana.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    motivo = models.CharField(max_length=255)

    class Meta:
        ordering = ["facultad", "dia_semana", "hora_inicio"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(hora_fin__gt=models.F("hora_inicio")),
                name="restriccion_facultad_fin_despues_inicio",
            ),
        ]


class Deporte(models.Model):
    """CU05 — Registro de deportes disponibles en la DUBSS."""

    nombre      = models.CharField(max_length=100, unique=True, verbose_name="nombre")
    descripcion = models.TextField(blank=True, verbose_name="descripción")
    cantidad_jugadores = models.PositiveSmallIntegerField(default=0)
    imagen      = models.ImageField(upload_to="deportes/", blank=True, null=True)
    activo      = models.BooleanField(default=True)
    creado_en   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Deporte"
        verbose_name_plural = "Deportes"
        ordering            = ["nombre"]

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    """CU04 — Categorías dentro de un deporte (Varones, Damas, Mixto, etc.)."""

    class Genero(models.TextChoices):
        VARONES = "VARONES", "Varones"
        DAMAS   = "DAMAS",   "Damas"
        MIXTO   = "MIXTO",   "Mixto"

    deporte     = models.ForeignKey(Deporte, on_delete=models.CASCADE,
                                    related_name="categorias")
    nombre      = models.CharField(max_length=100, verbose_name="nombre")
    genero      = models.CharField(max_length=10, choices=Genero.choices,
                                   default=Genero.VARONES)
    rango_edad  = models.CharField(max_length=20, default="GENERAL")
    descripcion = models.TextField(blank=True)
    activa      = models.BooleanField(default=True)

    class Meta:
        verbose_name        = "Categoría"
        verbose_name_plural = "Categorías"
        unique_together     = ["deporte", "nombre", "genero"]
        ordering            = ["deporte", "nombre"]

    def __str__(self):
        return f"{self.deporte} — {self.nombre} ({self.genero})"


class Campeonato(models.Model):
    """CU09 — Gestión de campeonatos universitarios."""

    class Estado(models.TextChoices):
        PLANIFICACION = "PLANIFICACION", "En planificación"
        INSCRIPCIONES = "INSCRIPCIONES", "Inscripciones abiertas"
        INSCRIPCION_CERRADA = "INSCRIPCION_CERRADA", "Inscripciones cerradas"
        EN_CURSO      = "EN_CURSO",      "En curso"
        FINALIZADO    = "FINALIZADO",    "Finalizado"
        CANCELADO     = "CANCELADO",     "Cancelado"

    class Formato(models.TextChoices):
        LIGA        = "LIGA",        "Liga (todos contra todos)"
        ELIMINACION = "ELIMINACION", "Eliminación directa"

    nombre          = models.CharField(max_length=200, verbose_name="nombre")
    categoria       = models.ForeignKey(Categoria, on_delete=models.PROTECT,
                                        related_name="campeonatos")
    estado          = models.CharField(max_length=20, choices=Estado.choices,
                                       default=Estado.PLANIFICACION)
    formato         = models.CharField(max_length=25, choices=Formato.choices,
                                       default=Formato.LIGA)
    fecha_inicio    = models.DateField(verbose_name="fecha de inicio")
    fecha_fin       = models.DateField(verbose_name="fecha de fin")
    max_equipos     = models.PositiveSmallIntegerField(default=8,
                                                        verbose_name="máximo de equipos")
    min_jugadores = models.PositiveSmallIntegerField(default=0)
    max_jugadores = models.PositiveSmallIntegerField(default=99)
    fecha_cierre_inscripcion = models.DateTimeField(null=True, blank=True)
    puntos_victoria = models.PositiveSmallIntegerField(default=3)
    puntos_empate = models.PositiveSmallIntegerField(default=1)
    puntos_derrota = models.PositiveSmallIntegerField(default=0)
    descripcion     = models.TextField(blank=True)
    imagen_banner   = models.ImageField(upload_to="campeonatos/", blank=True, null=True)
    creado_por      = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True,
                                        blank=True,
                                        related_name="campeonatos_creados")
    creado_en       = models.DateTimeField(auto_now_add=True)
    actualizado_en  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Campeonato"
        verbose_name_plural = "Campeonatos"
        ordering            = ["-fecha_inicio"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(min_jugadores__lte=models.F("max_jugadores")),
                name="campeonato_min_jugadores_lte_max",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.categoria.deporte})"

    @property
    def esta_activo(self):
        return self.estado == self.Estado.EN_CURSO


class Equipo(models.Model):
    """Equipo reutilizable que participa en campeonatos mediante Inscripcion."""

    nombre      = models.CharField(max_length=150, verbose_name="nombre del equipo")
    facultad    = models.ForeignKey(
        Facultad,
        on_delete=models.PROTECT,
        related_name="equipos",
    )
    logo        = models.ImageField(upload_to="equipos/logos/", blank=True, null=True)
    delegado    = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True,
                                    related_name="equipos_delegado",
                                    verbose_name="delegado responsable")
    color       = models.CharField(max_length=30, default="#000000")
    estado      = models.CharField(max_length=10, default="ACTIVO")
    creado_en   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Equipo"
        verbose_name_plural = "Equipos"
        constraints = [
            models.UniqueConstraint(
                fields=["nombre", "facultad"],
                name="equipo_unico_por_nombre_facultad",
            ),
        ]
        ordering            = ["nombre"]

    def __str__(self):
        return f"{self.nombre} — {self.facultad}"

    @property
    def cantidad_jugadores(self):
        return self.jugadores.filter(estado="ACTIVO").count()


class Inscripcion(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"

    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PENDIENTE)
    campeonato = models.ForeignKey(
        Campeonato,
        on_delete=models.CASCADE,
        related_name="inscripciones",
    )
    equipo = models.ForeignKey(
        Equipo,
        on_delete=models.CASCADE,
        related_name="inscripciones",
    )
    validado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inscripciones_validadas",
    )
    fecha_validacion = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Inscripción"
        verbose_name_plural = "Inscripciones"
        constraints = [
            models.UniqueConstraint(
                fields=["campeonato", "equipo"],
                name="inscripcion_unica_campeonato_equipo",
            ),
        ]
        ordering = ["-fecha_inscripcion"]


class FichaJugador(models.Model):
    """CU06 — Ficha de participante (jugador registrado en un equipo)."""

    equipo    = models.ForeignKey(Equipo,  on_delete=models.CASCADE,
                                  related_name="jugadores")
    usuario   = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fichas_jugador",
    )
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    carnet = models.CharField(max_length=30)
    registro = models.CharField(max_length=30)
    posicion = models.CharField(max_length=50)
    numero_camiseta = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="número de camiseta",
    )
    estado = models.CharField(max_length=12, default="ACTIVO")
    creado_en = models.DateTimeField(auto_now_add=True)
    partidos_sancion_restantes = models.PositiveSmallIntegerField(default=0)
    sancion_origen = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name        = "Ficha de Jugador"
        verbose_name_plural = "Fichas de Jugadores"
        constraints = [
            models.UniqueConstraint(
                fields=["equipo", "carnet"],
                name="ficha_unica_por_equipo_carnet",
            ),
        ]
        ordering = ["equipo", "numero_camiseta"]

    def __str__(self):
        camiseta = f"#{self.numero_camiseta} " if self.numero_camiseta is not None else ""
        return f"{camiseta}{self.nombre} {self.apellido} — {self.equipo}"
