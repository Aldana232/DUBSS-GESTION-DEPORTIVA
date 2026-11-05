from django.db import models


class RecordatorioEnviado(models.Model):
    """Registro de que ya se avisó de un partido (evita recordatorios duplicados si la tarea se repite)."""

    class Tipo(models.TextChoices):
        VEINTICUATRO_HORAS = "24H", "24 horas antes"
        DOS_HORAS = "2H", "2 horas antes"

    partido = models.ForeignKey("fixture.Partido", on_delete=models.CASCADE, related_name="recordatorios")
    tipo = models.CharField(max_length=3, choices=Tipo.choices)
    enviado_en = models.DateTimeField(auto_now_add=True)
    destinatarios = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Recordatorio enviado"
        verbose_name_plural = "Recordatorios enviados"
        constraints = [
            models.UniqueConstraint(fields=["partido", "tipo"], name="recordatorio_unico_por_partido_tipo"),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.partido_id}"
