from django.conf import settings
from django.db import models


class Bitacora(models.Model):
    class Accion(models.TextChoices):
        LOGIN = "LOGIN", "Inicio de sesión"
        LOGIN_FALLIDO = "LOGIN_FALLIDO", "Inicio de sesión fallido"
        CUENTA_BLOQUEADA = "CUENTA_BLOQUEADA", "Cuenta bloqueada"
        LOGOUT = "LOGOUT", "Cierre de sesión"
        CAMBIO_PASSWORD = "CAMBIO_PASSWORD", "Cambio de contraseña"
        CREAR = "CREAR", "Crear"
        EDITAR = "EDITAR", "Editar"
        ELIMINAR = "ELIMINAR", "Eliminar"
        CAMBIO_ROL = "CAMBIO_ROL", "Cambio de rol"
        CAMBIO_ESTADO = "CAMBIO_ESTADO", "Cambio de estado"
        GENERAR_FIXTURE = "GENERAR_FIXTURE", "Generar fixture"
        REGISTRAR_RESULTADO = "REGISTRAR_RESULTADO", "Registrar resultado"
        CORREGIR_RESULTADO = "CORREGIR_RESULTADO", "Corregir resultado"
        REGISTRAR_INCIDENCIA = "REGISTRAR_INCIDENCIA", "Registrar incidencia"
        EXPORTAR = "EXPORTAR", "Exportar"
        ML_PRED = "ML_PRED", "Predicción ML"
        ACCESO_DENEGADO = "ACCESO_DENEGADO", "Acceso denegado"

    class Resultado(models.TextChoices):
        OK = "OK", "Correcto"
        DENEGADO = "DENEGADO", "Denegado"
        ERROR = "ERROR", "Error"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_bitacora",
    )
    usuario_email = models.CharField(max_length=254, blank=True)
    accion = models.CharField(max_length=30, choices=Accion.choices, db_index=True)
    entidad = models.CharField(max_length=50, blank=True, db_index=True)
    entidad_id = models.PositiveIntegerField(null=True, blank=True)
    descripcion = models.TextField(blank=True)
    detalle = models.JSONField(default=dict, blank=True)
    resultado = models.CharField(
        max_length=10,
        choices=Resultado.choices,
        default=Resultado.OK,
        db_index=True,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Bitácora"
        verbose_name_plural = "Bitácora"

    def __str__(self):
        return f"[{self.fecha:%d/%m/%Y %H:%M}] {self.usuario_email or self.usuario} — {self.accion}"
