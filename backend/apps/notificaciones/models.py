from django.conf import settings
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


class Notificacion(models.Model):
    """
    Bandeja de avisos dentro de la app. Se crea para CADA destinatario de un aviso, sin depender de que haya
    correo, push o WhatsApp configurados: es el canal que nunca falla y donde se puede releer lo que pasó.
    """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificaciones")
    titulo = models.CharField(max_length=100)
    mensaje = models.CharField(max_length=500)
    datos = models.JSONField(default=dict, blank=True, help_text="Ej.: partido_id, para abrir el detalle al tocarla.")
    creada = models.DateTimeField(auto_now_add=True)
    leida_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ["-creada", "-id"]
        indexes = [
            models.Index(fields=["usuario", "leida_en"], name="notif_usuario_leida_idx"),
            models.Index(fields=["usuario", "-creada"], name="notif_usuario_creada_idx"),
        ]

    def __str__(self):
        return f"{self.titulo} → {self.usuario_id}"
