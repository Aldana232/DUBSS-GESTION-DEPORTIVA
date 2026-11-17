"""
Registro de la aceptación de los Términos y Condiciones y de la Política de Privacidad.

Cada aceptación es una fila nueva e inmutable (no se edita ni se borra): sirve de evidencia de QUÉ versión aceptó
la persona, CUÁNDO y desde DÓNDE. Si los documentos cambian (nueva versión), las filas viejas siguen ahí y la
persona vuelve a ser invitada a aceptar.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class AceptacionLegal(models.Model):
    class Documento(models.TextChoices):
        TERMINOS = "TERMINOS", "Términos y condiciones"
        PRIVACIDAD = "PRIVACIDAD", "Política de privacidad"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="aceptaciones_legales")
    documento = models.CharField(max_length=12, choices=Documento.choices)
    version = models.CharField(max_length=20, help_text="Versión del documento que se mostró y se aceptó.")
    aceptado_en = models.DateTimeField(default=timezone.now, editable=False)
    ip_origen = models.GenericIPAddressField(null=True, blank=True)
    agente = models.CharField(max_length=200, blank=True, help_text="Navegador o app desde donde se aceptó (recortado).")

    class Meta:
        verbose_name = "Aceptación legal"
        verbose_name_plural = "Aceptaciones legales"
        ordering = ["-aceptado_en"]
        constraints = [
            # Una sola aceptación por persona, documento y versión: repetir la petición no duplica la evidencia.
            models.UniqueConstraint(fields=["usuario", "documento", "version"], name="aceptacion_legal_unica"),
        ]

    def __str__(self):
        return f"{self.usuario_id} · {self.documento} v{self.version}"
