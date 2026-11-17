"""
Bandeja de salida (patrón «outbox») hacia n8n.

El evento se guarda en la base de datos y un worker de Celery lo entrega después. Así un aviso nunca se pierde
si n8n está caído, y una caída de n8n nunca bloquea ni rompe la operación que lo originó (registrar un
resultado, reprogramar un partido, etc.).
"""
import uuid

from django.db import models
from django.utils import timezone


class EventoSaliente(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        ENTREGADO = "ENTREGADO", "Entregado"
        FALLIDO = "FALLIDO", "Fallido (se agotaron los reintentos)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.CharField(max_length=40, help_text="Ej.: aviso, prueba.")
    payload = models.JSONField(default=dict)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    intentos = models.PositiveSmallIntegerField(default=0)
    proximo_intento = models.DateTimeField(default=timezone.now)
    ultimo_error = models.CharField(max_length=300, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    entregado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Evento saliente"
        verbose_name_plural = "Eventos salientes"
        ordering = ["-creado"]
        indexes = [models.Index(fields=["estado", "proximo_intento"], name="evento_pendientes_idx")]

    def __str__(self):
        return f"{self.tipo} · {self.get_estado_display()} · {self.creado:%d/%m %H:%M}"
