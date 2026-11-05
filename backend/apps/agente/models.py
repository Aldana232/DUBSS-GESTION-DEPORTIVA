"""
apps/agente/models.py
F7-01/F7-02 — Conversaciones del agente, propuestas calculadas por el servidor y acciones pendientes de confirmar.

Principio de seguridad: el LLM nunca escribe datos. Solo puede pedir una acción; el servidor calcula la propuesta,
la guarda aquí y una PERSONA la confirma. Lo que se ejecuta es lo guardado, no lo que el modelo diga después.
"""
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class ConversacionAgente(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversaciones_agente")
    titulo = models.CharField(max_length=120, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-actualizado_en"]

    def __str__(self):
        return self.titulo or f"Conversación {self.pk}"


class MensajeAgente(models.Model):
    class Rol(models.TextChoices):
        USUARIO = "USUARIO", "Usuario"
        AGENTE = "AGENTE", "Agente"

    conversacion = models.ForeignKey(ConversacionAgente, on_delete=models.CASCADE, related_name="mensajes")
    rol = models.CharField(max_length=10, choices=Rol.choices)
    contenido = models.TextField()
    # [{"herramienta", "ok", "resumen"}] — qué consultó o calculó el agente para responder (transparencia).
    pasos = models.JSONField(default=list, blank=True)
    # Reportes listos para descargar: [{"recurso", "id", "formato", "nombre"}].
    descargas = models.JSONField(default=list, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class PropuestaAgente(models.Model):
    """Resultado calculado por el servidor (p. ej. una reprogramación). El LLM solo recibe su id."""
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="propuestas_agente")
    conversacion = models.ForeignKey(ConversacionAgente, on_delete=models.CASCADE, related_name="propuestas")
    herramienta = models.CharField(max_length=40)
    datos = models.JSONField(default=dict)
    creado_en = models.DateTimeField(auto_now_add=True)


class AccionPendiente(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        CANCELADA = "CANCELADA", "Cancelada"
        EXPIRADA = "EXPIRADA", "Expirada"
        FALLIDA = "FALLIDA", "Fallida"      # al confirmar, el calendario ya no permitía el cambio

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="acciones_agente")
    conversacion = models.ForeignKey(ConversacionAgente, on_delete=models.CASCADE, related_name="acciones")
    mensaje = models.ForeignKey(MensajeAgente, on_delete=models.SET_NULL, null=True, blank=True, related_name="acciones")
    herramienta = models.CharField(max_length=40)
    resumen = models.CharField(max_length=300)      # redactado por el servidor, no por el modelo
    propuesta = models.JSONField(default=dict)      # lo único que se ejecuta al confirmar
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
    resultado = models.JSONField(default=dict, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()
    resuelta_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creado_en"]

    @staticmethod
    def nueva_expiracion():
        return timezone.now() + timedelta(minutes=settings.AGENTE_ACCION_MINUTOS)

    @property
    def vencida(self) -> bool:
        return self.estado == self.Estado.PENDIENTE and self.expira_en <= timezone.now()
