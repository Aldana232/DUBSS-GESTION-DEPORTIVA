"""
apps/agente/services/llm.py
F7-01 — Cliente del LLM con function calling (API compatible con OpenAI de Groq).

Solo Groq está soportado. Se usa un modelo `openai/gpt-oss-*`: con `reasoning_effort=low` responde rápido y
calcula bien las fechas relativas (el de 20B se equivocó con «el sábado» al probarlo; el de 120B no).
"""
from __future__ import annotations

import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GROQ_CHAT = "https://api.groq.com/openai/v1/chat/completions"
TIMEOUT_LLAMADA = 30
ESPERA_MAXIMA = 25        # segundos que se acepta esperar a que Groq libere cupo (el plan gratuito da 8 000 tokens/min)


class AgenteNoDisponible(RuntimeError):
    """El agente no puede responder ahora (sin configuración, sin cupo o el servicio no responde)."""


def disponible() -> bool:
    return settings.AGENTE_PROVIDER == "groq" and bool(settings.GROQ_API_KEY)


def chat(mensajes: list[dict], herramientas: list[dict], *, timeout: float = TIMEOUT_LLAMADA, espera_max: float = ESPERA_MAXIMA) -> dict:
    """
    Una vuelta al modelo. Devuelve {"content": str, "tool_calls": [{"id", "name", "arguments": str}]}.
    * Si Groq pide una pausa (429, límite de tokens por minuto), espera hasta `espera_max` s y reintenta.
    * Si el modelo generó una llamada a herramienta mal formada (400 conocido de Groq) o el servicio falla (5xx), reintenta.
    """
    if not disponible():
        raise AgenteNoDisponible("El agente no está configurado: falta la clave de Groq (GROQ_API_KEY).")
    carga = {
        "model": settings.AGENTE_MODEL, "messages": mensajes, "tools": herramientas, "tool_choice": "auto",
        "temperature": 0, "max_tokens": 1500,
        **({"reasoning_effort": "low"} if settings.AGENTE_MODEL.startswith("openai/gpt-oss") else {}),
    }
    cabeceras = {"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"}
    reintentos_400, reintentos_5xx, esperado = 0, 0, 0.0
    for _ in range(6):
        try:
            r = requests.post(GROQ_CHAT, headers=cabeceras, json=carga, timeout=timeout)
        except requests.RequestException as e:
            logger.warning("El agente no pudo contactar a Groq.", exc_info=True)
            raise AgenteNoDisponible("No se pudo contactar al servicio de IA. Intenta de nuevo en un momento.") from e
        if r.status_code == 429:
            try:
                pausa = float(r.headers.get("retry-after", 10))
            except ValueError:
                pausa = 10.0
            if esperado + pausa > espera_max:
                raise AgenteNoDisponible(f"El servicio de IA alcanzó su límite de uso. Intenta de nuevo en {int(pausa) + 1} segundos.")
            logger.info("Groq pidió esperar %.1fs (límite de uso); se reintenta.", pausa)
            time.sleep(pausa + 0.5)
            esperado += pausa + 0.5
            continue
        if r.status_code == 400 and reintentos_400 < 2:
            logger.info("Groq rechazó la generación (400); se reintenta: %s", r.text[:300])
            reintentos_400 += 1
            continue
        if r.status_code >= 500 and reintentos_5xx < 2:
            logger.info("Groq respondió %s; se reintenta: %s", r.status_code, r.text[:200])
            reintentos_5xx += 1
            time.sleep(2)
            continue
        if not r.ok:
            logger.warning("Groq respondió %s: %s", r.status_code, r.text[:300])
            raise AgenteNoDisponible("El servicio de IA no pudo procesar la consulta.")
        eleccion = r.json()["choices"][0]
        mensaje = eleccion["message"]
        if not mensaje.get("content") and not mensaje.get("tool_calls"):
            logger.warning("El modelo devolvió una respuesta vacía (finish_reason=%s).", eleccion.get("finish_reason"))
        return {
            "content": (mensaje.get("content") or "").strip(),
            "tool_calls": [
                {"id": c["id"], "name": c["function"]["name"], "arguments": c["function"].get("arguments") or "{}"}
                for c in (mensaje.get("tool_calls") or [])
            ],
        }
    raise AgenteNoDisponible("El servicio de IA no pudo procesar la consulta.")
