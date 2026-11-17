"""
Firma HMAC-SHA256 de los mensajes entre Django y n8n (en ambos sentidos).

Se firma `"{timestamp}.{cuerpo}"`: incluir la marca de tiempo impide que alguien que capture un mensaje lo
reenvíe más tarde (el receptor rechaza marcas con más de `TOLERANCIA_SEGUNDOS`). La comparación es de tiempo
constante para no filtrar la firma por diferencias de tiempo.
"""
import hashlib
import hmac
import time

TOLERANCIA_SEGUNDOS = 300


def firmar(secreto: str, marca: int, cuerpo: bytes) -> str:
    mac = hmac.new(secreto.encode(), f"{marca}.".encode() + cuerpo, hashlib.sha256)
    return "sha256=" + mac.hexdigest()


def verificar(secreto: str, marca: str | None, firma: str | None, cuerpo: bytes, ahora: float | None = None) -> bool:
    """True solo si la firma coincide Y la marca de tiempo es reciente."""
    if not secreto or not marca or not firma:
        return False
    try:
        marca_int = int(marca)
    except (TypeError, ValueError):
        return False
    if abs((ahora if ahora is not None else time.time()) - marca_int) > TOLERANCIA_SEGUNDOS:
        return False
    return hmac.compare_digest(firmar(secreto, marca_int, cuerpo), firma)
