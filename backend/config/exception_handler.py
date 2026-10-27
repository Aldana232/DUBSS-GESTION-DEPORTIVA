from rest_framework.views import exception_handler as drf_exception_handler

from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    request = context.get("request")
    usuario = getattr(request, "user", None)

    if (
        response is not None
        and response.status_code == 403
        and usuario is not None
        and usuario.is_authenticated
    ):
        registrar(
            Bitacora.Accion.ACCESO_DENEGADO,
            request=request,
            usuario=usuario,
            entidad="api",
            descripcion="Acceso denegado a un recurso.",
            detalle={
                "metodo": request.method,
                "ruta": request.path,
            },
            resultado=Bitacora.Resultado.DENEGADO,
        )

    return response
