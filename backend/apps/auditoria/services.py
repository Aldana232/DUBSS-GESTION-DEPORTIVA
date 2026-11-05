import logging

from rest_framework.throttling import BaseThrottle

from .models import Bitacora


logger = logging.getLogger(__name__)
CLAVES_SENSIBLES = ("password", "token", "refresh", "access", "secret")


def _sanear_detalle(valor):
    if isinstance(valor, dict):
        return {
            clave: (
                "***"
                if any(fragmento in str(clave).lower() for fragmento in CLAVES_SENSIBLES)
                else _sanear_detalle(contenido)
            )
            for clave, contenido in valor.items()
        }
    if isinstance(valor, list):
        return [_sanear_detalle(elemento) for elemento in valor]
    return valor


def registrar(
    accion,
    *,
    request=None,
    usuario=None,
    email="",
    modulo="",
    objeto_id=None,
    descripcion="",
    detalle=None,
    resultado="OK",
):
    try:
        if usuario is None and request is not None:
            usuario_solicitante = getattr(request, "user", None)
            if usuario_solicitante is not None and usuario_solicitante.is_authenticated:
                usuario = usuario_solicitante

        ip_origen = BaseThrottle().get_ident(request) if request is not None else None
        usuario_email = email or (getattr(usuario, "email", "") if usuario else "")
        return Bitacora.objects.create(
            usuario=usuario,
            usuario_email=usuario_email,
            accion=accion,
            modulo=modulo,
            objeto_id=objeto_id,
            descripcion=descripcion,
            detalle=_sanear_detalle({} if detalle is None else detalle),
            resultado=resultado,
            ip_origen=ip_origen,
        )
    except Exception:
        logger.exception("No se pudo registrar la acción de auditoría.")
        return None
