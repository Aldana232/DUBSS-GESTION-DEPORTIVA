"""
apps/asistente/services/interprete.py
F6-06 — Punto único para interpretar una orden: LLM si está disponible; reglas locales si no.
"""
from __future__ import annotations

from apps.asistente.services import intents, llm


def interpretar(texto: str, previo: dict | None = None, seleccion: dict | None = None) -> intents.Interpretacion:
    texto = " ".join((texto or "").split())[:500]
    if previo and previo.get("intencion"):
        # Seguimiento de una aclaración: ya se sabe qué se pide, solo falta elegir la entidad.
        return intents.completar(texto, previo.get("proveedor", "reglas"), previo["intencion"],
                                 previo.get("formato"), {}, seleccion)

    respuesta = llm.interpretar_con_llm(texto)
    if respuesta is not None:
        if respuesta["intencion"] == "desconocida":
            return intents.completar(texto, "llm", None, None, {})
        formato = respuesta.get("formato") or intents.detectar_formato(intents.normalizar(texto))
        return intents.completar(texto, "llm", respuesta["intencion"], formato, {
            "campeonato": respuesta.get("campeonato"), "equipo": respuesta.get("equipo"), "jugador": respuesta.get("jugador"),
        }, seleccion)
    return intents.interpretar_por_reglas(texto, seleccion=seleccion)
