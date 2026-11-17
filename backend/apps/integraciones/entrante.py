"""
Mensajes que llegan por WhatsApp (n8n los reenvía firmados). Es una consulta de SOLO LECTURA con pocas órdenes
fijas: no hay modelo de lenguaje ni acciones que cambien datos, así que un mensaje ajeno no puede hacer daño.
La única escritura permitida es que la persona se dé de baja de sus propios avisos.
"""
from __future__ import annotations

import unicodedata

from django.db.models import Q
from django.utils import timezone

from apps.fixture.models import Partido, Resultado
from apps.users.models import Usuario

AYUDA = (
    "Soy el asistente de la DUBSS. Escribe:\n"
    "• PARTIDOS: tus próximos partidos\n"
    "• RESULTADOS: los últimos resultados\n"
    "• BAJA: dejar de recibir avisos por WhatsApp"
)
NO_REGISTRADO = ("Este número no está vinculado a una cuenta de la DUBSS con WhatsApp activado. "
                 "Entra al sistema, abre tu perfil y activa los avisos por WhatsApp.")
BAJA = ("Listo, dejaste de recibir avisos por WhatsApp. Puedes volver a activarlos en tu perfil del sistema.")
DESCONOCIDO = "No entendí tu mensaje.\n" + AYUDA
MAX_TEXTO = 200

_BAJA = {"baja", "stop", "salir", "detener"}      # frases explícitas: un simple «no» no debe darte de baja
_AYUDA = {"ayuda", "hola", "menu", "help", "buenas", "inicio"}
_PARTIDOS = {"partidos", "partido", "proximos", "calendario", "fixture"}
_RESULTADOS = {"resultados", "resultado", "marcadores"}


def _limpio(texto: str) -> str:
    t = unicodedata.normalize("NFKD", (texto or "")[:MAX_TEXTO]).encode("ascii", "ignore").decode().lower()
    return " ".join(t.split())


def usuario_por_whatsapp(numero: str) -> Usuario | None:
    return Usuario.objects.filter(whatsapp=numero, acepta_whatsapp=True, is_active=True).first() if numero else None


def _fecha(p: Partido) -> str:
    return timezone.localtime(p.fecha_hora).strftime("%d/%m %H:%M")


def _proximos(usuario: Usuario) -> str:
    qs = Partido.objects.filter(estado=Partido.Estado.PROGRAMADO, fecha_hora__gt=timezone.now(),
                                equipo_local__isnull=False, equipo_visitante__isnull=False)
    if usuario.rol == Usuario.Rol.DELEGADO:
        qs = qs.filter(Q(equipo_local__delegado=usuario) | Q(equipo_visitante__delegado=usuario))
    lineas = [f"{_fecha(p)} · {p.equipo_local.nombre} vs {p.equipo_visitante.nombre}" + (f" ({p.cancha.nombre})" if p.cancha else "")
              for p in qs.select_related("equipo_local", "equipo_visitante", "cancha").order_by("fecha_hora")[:5]]
    return "Próximos partidos:\n" + "\n".join(lineas) if lineas else "No hay partidos programados por ahora."


def _resultados(usuario: Usuario) -> str:
    qs = Resultado.objects.select_related("partido__equipo_local", "partido__equipo_visitante").order_by("-partido__fecha_hora")
    if usuario.rol == Usuario.Rol.DELEGADO:
        qs = qs.filter(Q(partido__equipo_local__delegado=usuario) | Q(partido__equipo_visitante__delegado=usuario))
    lineas = [f"{r.partido.equipo_local.nombre} {r.goles_local} - {r.goles_visitante} {r.partido.equipo_visitante.nombre}" for r in qs[:5]]
    return "Últimos resultados:\n" + "\n".join(lineas) if lineas else "Todavía no hay resultados."


def responder(numero: str, texto: str) -> tuple[str, str]:
    """Devuelve (respuesta, intención). Intención: baja | ayuda | partidos | resultados | desconocido | no_registrado."""
    usuario = usuario_por_whatsapp(numero)
    if usuario is None:
        return NO_REGISTRADO, "no_registrado"
    palabra = _limpio(texto)
    if palabra in _BAJA:
        usuario.acepta_whatsapp = False
        usuario.save(update_fields=["acepta_whatsapp"])
        return BAJA, "baja"
    if palabra in _AYUDA:
        return AYUDA, "ayuda"
    if palabra in _PARTIDOS:
        return _proximos(usuario), "partidos"
    if palabra in _RESULTADOS:
        return _resultados(usuario), "resultados"
    return DESCONOCIDO, "desconocido"
