"""
Cola de eventos hacia n8n y su entrega.

Flujo:  operación del sistema → `encolar_aviso()` → fila EventoSaliente (misma transacción) →
        Celery `integraciones.despachar_eventos` → POST firmado a n8n → n8n envía por WhatsApp.

Garantía: «al menos una vez». Si n8n responde mal o no responde, se reintenta con espera creciente; n8n recibe
el id del evento en `X-DUBSS-Event-Id` por si quiere descartar repetidos.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import timedelta
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .firma import firmar
from .models import EventoSaliente

logger = logging.getLogger(__name__)

TIMEOUT_SEG = 10
ARRANQUE_ARRENDAMIENTO = timedelta(minutes=2)   # mientras se envía, nadie más toma el evento
POR_LOTE = 50
DESTINATARIOS_POR_EVENTO = 50


def configurado() -> bool:
    """Hay URL de n8n y secreto. Sin ambos, la integración está apagada y no se guarda ningún evento."""
    return bool(settings.N8N_URL_EVENTOS and settings.N8N_SECRETO)


def host_destino() -> str:
    return urlsplit(settings.N8N_URL_EVENTOS).netloc if settings.N8N_URL_EVENTOS else ""


def _despertar_worker() -> None:
    """Pide la entrega inmediata; si el broker no responde no pasa nada: el beat lo recoge en un minuto."""
    try:
        from .tasks import despachar_eventos
        despachar_eventos.delay()
    except Exception:  # noqa: BLE001
        logger.warning("No se pudo avisar al worker de integraciones; el beat entregará el evento.")


def encolar(tipo: str, payload: dict) -> EventoSaliente | None:
    if not configurado():
        return None
    evento = EventoSaliente.objects.create(tipo=tipo, payload=payload)
    transaction.on_commit(_despertar_worker)
    return evento


def destinatarios_whatsapp(usuarios) -> list[dict]:
    """
    Solo quien dio su número Y aceptó recibir avisos. Se envía lo mínimo necesario (nombre y número):
    ni correo, ni rol, ni facultad.
    """
    vistos, salida = set(), []
    for u in usuarios:
        if u is None or not u.is_active or not u.acepta_whatsapp or not u.whatsapp or u.whatsapp in vistos:
            continue
        vistos.add(u.whatsapp)
        salida.append({"nombre": u.nombre, "whatsapp": u.whatsapp})
    return salida


def encolar_aviso(usuarios, titulo: str, mensaje: str, datos: dict | None = None) -> int:
    """Encola el aviso para los usuarios con WhatsApp activo. Devuelve cuántos destinatarios quedaron en cola."""
    if not configurado():
        return 0
    destinatarios = destinatarios_whatsapp(usuarios)
    for i in range(0, len(destinatarios), DESTINATARIOS_POR_EVENTO):
        encolar("aviso", {
            "titulo": titulo, "mensaje": mensaje, "datos": datos or {},
            "destinatarios": destinatarios[i:i + DESTINATARIOS_POR_EVENTO],
        })
    return len(destinatarios)


def _sobre(evento: EventoSaliente) -> bytes:
    sobre = {"version": 1, "id": str(evento.id), "tipo": evento.tipo,
             "creado": evento.creado.isoformat(), "datos": evento.payload}
    return json.dumps(sobre, ensure_ascii=False, separators=(",", ":")).encode()


def _enviar(evento: EventoSaliente) -> tuple[bool, str]:
    cuerpo = _sobre(evento)
    marca = int(time.time())
    cabeceras = {
        "Content-Type": "application/json; charset=utf-8",
        "X-DUBSS-Event-Id": str(evento.id),
        "X-DUBSS-Event-Type": evento.tipo,
        "X-DUBSS-Timestamp": str(marca),
        "X-DUBSS-Signature": firmar(settings.N8N_SECRETO, marca, cuerpo),
    }
    try:
        r = requests.post(settings.N8N_URL_EVENTOS, data=cuerpo, headers=cabeceras, timeout=TIMEOUT_SEG)
    except requests.RequestException as e:
        return False, f"Sin conexión con n8n ({type(e).__name__})."
    if 200 <= r.status_code < 300:
        return True, ""
    return False, f"n8n respondió HTTP {r.status_code}."


def _reservar(limite: int) -> list[EventoSaliente]:
    """Toma los eventos vencidos y les pone un arrendamiento, para que dos workers no envíen el mismo."""
    ahora = timezone.now()
    with transaction.atomic():
        eventos = list(
            EventoSaliente.objects.select_for_update(skip_locked=True)
            .filter(estado=EventoSaliente.Estado.PENDIENTE, proximo_intento__lte=ahora)
            .order_by("creado")[:limite]
        )
        for e in eventos:
            e.intentos += 1
            e.proximo_intento = ahora + ARRANQUE_ARRENDAMIENTO
            e.save(update_fields=["intentos", "proximo_intento"])
    return eventos


def despachar(limite: int = POR_LOTE) -> dict:
    """Entrega los eventos pendientes. Devuelve {"entregados", "reintentos", "fallidos"}."""
    resumen = {"entregados": 0, "reintentos": 0, "fallidos": 0}
    if not configurado():
        return resumen
    esperas = list(settings.INTEGRACION_REINTENTOS_MINUTOS)
    for evento in _reservar(limite):
        ok, error = _enviar(evento)
        if ok:
            evento.estado, evento.entregado_en, evento.ultimo_error = EventoSaliente.Estado.ENTREGADO, timezone.now(), ""
            resumen["entregados"] += 1
        elif evento.intentos > len(esperas):
            evento.estado, evento.ultimo_error = EventoSaliente.Estado.FALLIDO, error
            resumen["fallidos"] += 1
            logger.error("Evento %s agotó los reintentos: %s", evento.id, error)
        else:
            evento.ultimo_error = error
            evento.proximo_intento = timezone.now() + timedelta(minutes=esperas[evento.intentos - 1])
            resumen["reintentos"] += 1
        evento.save(update_fields=["estado", "entregado_en", "ultimo_error", "proximo_intento"])
    return resumen


def enviar_prueba(mensaje: str, usuario) -> EventoSaliente:
    """Evento de prueba para comprobar el enlace con n8n (y, si el usuario activó WhatsApp, el mensaje real)."""
    evento = EventoSaliente.objects.create(
        tipo="prueba",
        payload={"titulo": "Prueba de conexión", "mensaje": mensaje, "datos": {},
                 "destinatarios": destinatarios_whatsapp([usuario])},
    )
    ok, error = _enviar(evento)
    evento.intentos = 1
    if ok:
        evento.estado, evento.entregado_en = EventoSaliente.Estado.ENTREGADO, timezone.now()
    else:
        evento.ultimo_error = error
        evento.estado = EventoSaliente.Estado.FALLIDO       # una prueba no se reintenta sola
    evento.save()
    return evento
