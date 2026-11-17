"""Normalización de números de WhatsApp al formato internacional sin «+» (E.164), como lo pide la API de Meta."""
import re

from django.conf import settings


def normalizar_whatsapp(valor: str) -> str:
    """
    «70012345», «+591 700-12345» y «59170012345» → «59170012345».
    Devuelve «» si el texto está vacío; lanza ValueError si no parece un número válido.
    """
    bruto = (valor or "").strip()
    if not bruto:
        return ""
    if re.search(r"[^\d\s+\-().]", bruto):
        raise ValueError("Escribe solo números (puedes usar +, espacios o guiones).")
    digitos = re.sub(r"\D", "", bruto)
    if bruto.startswith("00"):
        digitos = digitos[2:]
    elif not bruto.startswith("+") and len(digitos) == 8 and digitos[0] in "67":
        digitos = settings.WHATSAPP_PAIS_DEFECTO + digitos      # móvil boliviano sin código de país
    if not 8 <= len(digitos) <= 15 or digitos.startswith("0"):
        raise ValueError("El número no es válido. Incluye el código de país, por ejemplo 59170012345.")
    return digitos
