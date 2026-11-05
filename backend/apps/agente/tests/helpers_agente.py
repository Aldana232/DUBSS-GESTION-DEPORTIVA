"""Escenarios y dobles de prueba del agente: calendario en curso, clima simulado y LLM guionado."""
from datetime import datetime, time, timedelta
from types import SimpleNamespace

from django.utils import timezone

from apps.agente.models import ConversacionAgente
from apps.agente.services import herramientas
from apps.deportes.models import Campeonato
from apps.fixture.models import Partido
from apps.fixture.tests.helpers import crear_canchas, crear_escenario, crear_equipo
from apps.instalaciones.models import Cancha
from apps.ml.services.clima import ServicioClima


def dia(n: int):
    """Fecha local dentro de n días."""
    return timezone.localdate() + timedelta(days=n)


def a_las(n_dias: int, hora: int, minuto: int = 0):
    return timezone.make_aware(datetime.combine(dia(n_dias), time(hora, minuto)))


def crear_partido(esc, local, visitante, cancha, cuando, jornada=1, **extra):
    return Partido.objects.create(
        campeonato=esc.campeonato, equipo_local=local, equipo_visitante=visitante, cancha=cancha,
        fecha_hora=cuando, jornada=jornada, duracion_min=90, **extra)


def escenario_en_curso(equipos=4, canchas=2, techadas=0):
    """Campeonato EN_CURSO con equipos y canchas (las últimas `techadas` son techadas)."""
    esc = crear_escenario(equipos=equipos, canchas=canchas, estado=Campeonato.Estado.EN_CURSO)
    for c in esc.canchas[len(esc.canchas) - techadas:]:
        Cancha.objects.filter(pk=c.pk).update(techada=True)
    esc.canchas = list(Cancha.objects.filter(pk__in=[c.pk for c in esc.canchas]).order_by("pk"))
    return esc


def serie_con_lluvia(dias_lluviosos=()):
    """Pronóstico horario de 16 días: seco, salvo los días indicados (lluvia fuerte todo el día)."""
    lluviosos = {dia(n) for n in dias_lluviosos}
    inicio = timezone.make_aware(datetime.combine(timezone.localdate(), time.min))
    return [{"momento": inicio + timedelta(hours=h), "temp": 25.0, "viento": 10.0, "prob_lluvia": 0,
             "lluvia": 6.0 if (inicio + timedelta(hours=h)).date() in lluviosos else 0.0} for h in range(24 * 16)]


def simular_clima(monkeypatch, dias_lluviosos=()):
    monkeypatch.setattr(ServicioClima, "serie", lambda self: serie_con_lluvia(dias_lluviosos))


def clima_caido(monkeypatch):
    def falla(self):
        raise RuntimeError("sin red")
    monkeypatch.setattr(ServicioClima, "serie", falla)


def contexto(usuario):
    conv = ConversacionAgente.objects.create(usuario=usuario)
    return herramientas.Contexto(usuario=usuario, conversacion=conv)


class LlmGuionado:
    """Doble del LLM: devuelve respuestas predefinidas en orden y guarda lo que recibió."""

    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.recibido = []

    def __call__(self, mensajes, herramientas_, timeout=30):
        self.recibido.append([dict(m) for m in mensajes])
        return self.respuestas.pop(0) if self.respuestas else {"content": "Fin.", "tool_calls": []}


def llamada(nombre, **argumentos):
    import json
    return {"content": "", "tool_calls": [{"id": f"c{nombre}", "name": nombre, "arguments": json.dumps(argumentos)}]}


def texto(contenido):
    return {"content": contenido, "tool_calls": []}


__all__ = ["SimpleNamespace", "crear_canchas", "crear_equipo"]
