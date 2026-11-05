"""
apps/notificaciones/fcm.py
RF25 / F6-04 — Notificaciones push con Firebase Cloud Messaging HTTP v1.

La API «legada» (`/fcm/send` con server key) fue dada de baja por Google. HTTP v1 usa una cuenta de
servicio: se descarga desde Firebase Console → Configuración del proyecto → Cuentas de servicio, y
se apunta a ella con `FCM_CREDENTIALS_FILE`. Sin ese archivo el push queda deshabilitado (el
sistema sigue avisando por correo) y la interfaz lo indica.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

ALCANCE = "https://www.googleapis.com/auth/firebase.messaging"
URL_ENVIO = "https://fcm.googleapis.com/v1/projects/{proyecto}/messages:send"
LIMITE_CUERPO = 240

_candado = threading.Lock()
_credenciales = None


class PushNoConfigurado(RuntimeError):
    """Falta el archivo de la cuenta de servicio o no es válido."""


def configurado() -> bool:
    ruta = settings.FCM_CREDENTIALS_FILE
    return bool(ruta) and Path(ruta).is_file()


def _cargar_credenciales():
    global _credenciales
    with _candado:
        if _credenciales is None:
            if not configurado():
                raise PushNoConfigurado("FCM_CREDENTIALS_FILE no apunta a un archivo de cuenta de servicio.")
            from google.oauth2 import service_account

            try:
                _credenciales = service_account.Credentials.from_service_account_file(
                    settings.FCM_CREDENTIALS_FILE, scopes=[ALCANCE])
            except (ValueError, OSError) as e:
                raise PushNoConfigurado(f"La cuenta de servicio de Firebase no es válida: {e}") from e
        return _credenciales


def _token_de_acceso() -> tuple[str, str]:
    from google.auth.transport.requests import Request

    credenciales = _cargar_credenciales()
    if not credenciales.valid:
        credenciales.refresh(Request())
    return credenciales.token, credenciales.project_id


def enviar_push(tokens: list[str], titulo: str, cuerpo: str, datos: dict | None = None) -> dict:
    """
    Envía la notificación a cada token. Devuelve
    {"enviados": n, "invalidos": [tokens a limpiar], "fallidos": n, "configurado": bool}.
    Un token inválido (app desinstalada) no interrumpe el envío al resto.
    """
    tokens = [t for t in dict.fromkeys(tokens) if t]
    resultado = {"enviados": 0, "invalidos": [], "fallidos": 0, "configurado": configurado()}
    if not tokens or not resultado["configurado"]:
        return resultado
    try:
        acceso, proyecto = _token_de_acceso()
    except Exception:  # noqa: BLE001 - credenciales rechazadas o sin red: el push se omite, el correo sigue
        logger.warning("No se pudo autenticar con Firebase; no se envía el push.", exc_info=True)
        resultado["fallidos"] = len(tokens)
        return resultado

    mensaje_base = {
        "notification": {"title": titulo[:100], "body": cuerpo[:LIMITE_CUERPO]},
        "data": {str(k): str(v) for k, v in (datos or {}).items()},
    }
    sesion = requests.Session()
    sesion.headers.update({"Authorization": f"Bearer {acceso}", "Content-Type": "application/json"})
    for token in tokens:
        try:
            r = sesion.post(URL_ENVIO.format(proyecto=proyecto), json={"message": {**mensaje_base, "token": token}}, timeout=10)
        except requests.RequestException:
            resultado["fallidos"] += 1
            continue
        if r.ok:
            resultado["enviados"] += 1
            continue
        estado = ""
        try:
            estado = r.json().get("error", {}).get("status", "")
        except ValueError:
            pass
        if r.status_code == 404 or estado in ("NOT_FOUND", "UNREGISTERED", "INVALID_ARGUMENT"):
            resultado["invalidos"].append(token)       # token muerto: se limpia para no insistir
        else:
            resultado["fallidos"] += 1
    return resultado


def limpiar_tokens_invalidos(tokens: list[str]) -> int:
    from apps.users.models import Usuario

    return Usuario.objects.filter(fcm_token__in=tokens).update(fcm_token="") if tokens else 0
