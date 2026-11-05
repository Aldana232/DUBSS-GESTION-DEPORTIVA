"""
apps/fixture/idempotencia.py
F7-06 — Escrituras idempotentes con la cabecera `Idempotency-Key`.

Garantías:
* Sin cabecera, el endpoint se comporta como siempre.
* Misma clave + mismo contenido: se devuelve la respuesta guardada (cabecera `Idempotent-Replayed: true`) sin volver
  a ejecutar nada. Así reenviar una acción cuyo resultado se desconoce nunca la duplica.
* Misma clave + otro contenido (o ruta): 422. Una clave identifica UNA acción.
* Dos envíos simultáneos con la misma clave: el segundo espera al primero (índice único de PostgreSQL) y recibe su
  respuesta guardada.
* Solo se guardan las respuestas exitosas (2xx). Si la operación falla, la clave queda libre y el reintento se evalúa
  de nuevo contra el estado actual. La clave es por persona: nadie puede reutilizar ni adivinar la de otra.
"""
from __future__ import annotations

import hashlib
import json
import re

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from apps.fixture.models import OperacionIdempotente

CABECERA = "Idempotency-Key"
FORMATO_CLAVE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


class ClaveInvalida(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "La clave de idempotencia debe tener entre 8 y 64 caracteres (letras, números, guion o guion bajo)."


class ClaveReutilizada(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Esa clave de idempotencia ya se usó con otros datos."


def _huella(request) -> str:
    cuerpo = json.dumps(request.data, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(f"{request.method}|{request.path}|{cuerpo}".encode()).hexdigest()


def _repetir(operacion: OperacionIdempotente) -> Response:
    respuesta = Response(operacion.respuesta, status=operacion.codigo)
    respuesta["Idempotent-Replayed"] = "true"
    return respuesta


def ejecutar_idempotente(request, ejecutar) -> Response:
    """Corre `ejecutar()` (devuelve una Response) una sola vez por clave."""
    clave = request.headers.get(CABECERA)
    if not clave:
        return ejecutar()
    if not FORMATO_CLAVE.match(clave):
        raise ClaveInvalida()
    huella = _huella(request)

    with transaction.atomic():
        try:
            with transaction.atomic():                      # punto de guardado: aísla SOLO el choque de clave duplicada
                operacion = OperacionIdempotente.objects.create(
                    usuario=request.user, clave=clave, metodo=request.method, ruta=request.path[:200], huella=huella)
        except IntegrityError:
            # Otra transacción con esta clave ya terminó (si la anterior hubiera fallado, la clave estaría libre).
            existente = OperacionIdempotente.objects.get(usuario=request.user, clave=clave)
            if existente.huella != huella:
                raise ClaveReutilizada() from None
            return _repetir(existente)

        respuesta = ejecutar()
        if not 200 <= respuesta.status_code < 300:
            transaction.set_rollback(True)                  # la operación no se aplicó: la clave vuelve a quedar libre
            return respuesta
        operacion.codigo, operacion.respuesta = respuesta.status_code, respuesta.data
        operacion.save(update_fields=["codigo", "respuesta"])
        return respuesta
