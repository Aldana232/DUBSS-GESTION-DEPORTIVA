"""
apps/notificaciones/services.py
Avisos del sistema a usuarios: correo y notificación push (FCM v1).

Nunca lanza excepción: un fallo de correo o de push no debe revertir la operación de negocio que lo origina.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail

from apps.notificaciones import fcm

logger = logging.getLogger(__name__)


def email_configurado() -> bool:
    """Hay cuenta de correo, o el backend no es SMTP (consola/pruebas)."""
    return bool(settings.EMAIL_HOST_USER) or "smtp" not in settings.EMAIL_BACKEND


def notificar_usuarios(usuarios, titulo: str, mensaje: str, datos: dict | None = None) -> dict:
    """
    Avisa por correo y por push a los usuarios activos. Devuelve cuántos recibieron cada canal:
    {"usuarios", "email", "push", "push_configurado", "email_configurado"}.
    """
    destinatarios = {u.pk: u for u in usuarios if u is not None and u.is_active}.values()
    resumen = {"usuarios": len(destinatarios), "email": 0, "push": 0,
               "push_configurado": fcm.configurado(), "email_configurado": email_configurado()}
    if not destinatarios:
        return resumen

    emails = sorted({u.email for u in destinatarios if u.email})
    if emails and resumen["email_configurado"]:
        try:
            send_mail(subject=titulo, message=mensaje, from_email=settings.EMAIL_HOST_USER or None,
                      recipient_list=emails, fail_silently=True)
            resumen["email"] = len(emails)
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo enviar el correo '%s'.", titulo)

    tokens = [u.fcm_token for u in destinatarios if getattr(u, "fcm_token", "")]
    if tokens and resumen["push_configurado"]:
        try:
            r = fcm.enviar_push(tokens, titulo, mensaje, datos)
            resumen["push"] = r["enviados"]
            fcm.limpiar_tokens_invalidos(r["invalidos"])
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo enviar el push '%s'.", titulo)
    return resumen
