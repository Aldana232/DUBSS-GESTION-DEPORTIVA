from django.conf import settings
from django.db import IntegrityError, transaction

from .models import AceptacionLegal

DOCUMENTOS = [AceptacionLegal.Documento.TERMINOS, AceptacionLegal.Documento.PRIVACIDAD]
RUTAS = {
    AceptacionLegal.Documento.TERMINOS: "/terminos",
    AceptacionLegal.Documento.PRIVACIDAD: "/privacidad",
}


def version_vigente() -> str:
    return settings.LEGAL_VERSION


def aceptacion_vigente(usuario):
    """La última aceptación de la versión vigente (la de los términos), o None si falta alguno de los dos documentos."""
    filas = {a.documento: a for a in AceptacionLegal.objects.filter(usuario=usuario, version=version_vigente())}
    if set(filas) != set(DOCUMENTOS):
        return None
    return max(filas.values(), key=lambda a: a.aceptado_en)


def pendiente(usuario) -> bool:
    return aceptacion_vigente(usuario) is None


def aceptar(usuario, *, ip: str | None, agente: str) -> tuple[bool, AceptacionLegal]:
    """
    Registra la aceptación de ambos documentos en la versión vigente. Es idempotente: si ya estaba aceptada
    devuelve (False, aceptacion) sin crear filas nuevas. Devuelve (creada, aceptacion).
    """
    existente = aceptacion_vigente(usuario)
    if existente is not None:
        return False, existente
    with transaction.atomic():
        for doc in DOCUMENTOS:
            try:
                with transaction.atomic():
                    AceptacionLegal.objects.create(usuario=usuario, documento=doc, version=version_vigente(),
                                                   ip_origen=ip, agente=(agente or "")[:200])
            except IntegrityError:        # dos pestañas aceptaron a la vez: la otra ya la guardó
                continue
    return True, aceptacion_vigente(usuario)
