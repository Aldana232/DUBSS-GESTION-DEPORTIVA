from django.conf import settings
from django.db import models


class Queja(models.Model):
    class Tipo(models.TextChoices):
        QUEJA = "QUEJA", "Queja"
        APELACION = "APELACION", "Apelación"

    class Estado(models.TextChoices):
        ABIERTA = "ABIERTA", "Abierta"
        EN_REVISION = "EN_REVISION", "En revisión"
        RESUELTA = "RESUELTA", "Resuelta"
        RECHAZADA = "RECHAZADA", "Rechazada"

    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    descripcion = models.TextField()
    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.ABIERTA,
    )
    resolucion = models.TextField(null=True, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    resuelta_en = models.DateTimeField(null=True, blank=True)
    admin_resuelve = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quejas_resueltas",
    )
    delegado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quejas_presentadas",
    )
    encuentro = models.ForeignKey(
        "fixture.Partido",
        on_delete=models.CASCADE,
        related_name="quejas",
    )

    class Meta:
        ordering = ["-fecha_hora"]
        constraints = [
            models.UniqueConstraint(
                fields=["encuentro", "tipo"],
                name="queja_unica_por_encuentro_tipo",
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} — partido {self.encuentro_id}"
