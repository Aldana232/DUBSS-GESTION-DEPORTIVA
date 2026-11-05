"""
apps/fixture/services/resultados.py
RF12 — Registrar, corregir y eliminar resultados.

Cada operación es atómica: el resultado, el estado del partido, el avance del
ganador (eliminación directa), el descuento de sanciones y la tabla de
posiciones se guardan juntos o no se guarda nada. La tabla se recalcula dentro
de la misma transacción (no en `on_commit`): así nunca queda desfasada del
resultado y la operación es idempotente.
"""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.deportes.models import Campeonato
from apps.fixture.models import Partido, Resultado
from apps.fixture.services import sanciones, tabla

CAMPOS = ("goles_local", "goles_visitante", "penales_local", "penales_visitante",
          "walkover", "observaciones")


def es_eliminacion(partido: Partido) -> bool:
    return partido.campeonato.formato == Campeonato.Formato.ELIMINACION


def resumen(resultado: Resultado) -> dict:
    """Valores del resultado para la bitácora."""
    return {campo: getattr(resultado, campo) for campo in CAMPOS}


def _siguientes(partido: Partido):
    return list(partido.siguiente_como_local.all()) + list(
        partido.siguiente_como_visitante.all()
    )


def _bloquear_si_siguiente_jugado(partido: Partido, nuevo_ganador):
    """Impide cambiar un ganador que ya avanzó y jugó la ronda siguiente."""
    for siguiente in _siguientes(partido):
        ya_jugado = siguiente.estado in (
            Partido.Estado.FINALIZADO, Partido.Estado.WALKOVER, Partido.Estado.EN_CURSO,
        )
        lado = "equipo_local" if siguiente.partido_origen_local_id == partido.pk \
            else "equipo_visitante"
        if ya_jugado and getattr(siguiente, lado) != nuevo_ganador:
            raise ValidationError({
                "detail": "No se puede modificar el resultado: el ganador ya avanzó y "
                          "jugó la siguiente ronda. Corrige primero ese partido."
            })


def avanzar_ganador(partido: Partido):
    """Coloca al ganador en el partido de la siguiente ronda (eliminación directa)."""
    ganador = partido.resultado.ganador if hasattr(partido, "resultado") else None
    for siguiente in partido.siguiente_como_local.all():
        siguiente.equipo_local = ganador
        siguiente.save(update_fields=["equipo_local"])
    for siguiente in partido.siguiente_como_visitante.all():
        siguiente.equipo_visitante = ganador
        siguiente.save(update_fields=["equipo_visitante"])


def _estado_final(resultado: Resultado) -> str:
    return Partido.Estado.WALKOVER if resultado.walkover else Partido.Estado.FINALIZADO


def _bloquear(partido: Partido) -> Partido:
    return Partido.objects.select_for_update(of=("self",)).select_related(
        "campeonato", "equipo_local", "equipo_visitante"
    ).get(pk=partido.pk)


@transaction.atomic
def registrar_resultado(partido: Partido, datos: dict, usuario) -> Resultado:
    partido = _bloquear(partido)
    if hasattr(partido, "resultado"):
        raise ValidationError({"detail": "Este partido ya tiene resultado. Usa PATCH para corregirlo."})
    resultado = Resultado.objects.create(partido=partido, registrado_por=usuario, **datos)
    partido.estado = _estado_final(resultado)
    partido.save(update_fields=["estado", "actualizado_en"])
    if not resultado.walkover:
        sanciones.descontar_sanciones(partido)
    if es_eliminacion(partido):
        avanzar_ganador(partido)
    tabla.recalcular(partido.campeonato)
    return resultado


@transaction.atomic
def corregir_resultado(partido: Partido, datos: dict) -> tuple[Resultado, dict]:
    """Aplica `datos` al resultado existente. Devuelve (resultado, valores_anteriores)."""
    partido = _bloquear(partido)
    resultado = Resultado.objects.get(partido=partido)
    anterior = resumen(resultado)
    for campo, valor in datos.items():
        setattr(resultado, campo, valor)
    if es_eliminacion(partido):
        _bloquear_si_siguiente_jugado(partido, resultado.ganador)
    resultado.save()
    partido.estado = _estado_final(resultado)
    partido.save(update_fields=["estado", "actualizado_en"])
    if es_eliminacion(partido):
        avanzar_ganador(partido)
    tabla.recalcular(partido.campeonato)
    return resultado, anterior


@transaction.atomic
def eliminar_resultado(partido: Partido) -> dict:
    """Borra el resultado y devuelve el partido a PROGRAMADO. Devuelve los valores borrados."""
    partido = _bloquear(partido)
    resultado = Resultado.objects.get(partido=partido)
    anterior = resumen(resultado)
    if es_eliminacion(partido):
        _bloquear_si_siguiente_jugado(partido, None)
        resultado.delete()
        partido = Partido.objects.select_related("campeonato").get(pk=partido.pk)
        avanzar_ganador(partido)  # sin resultado: libera las plazas de la siguiente ronda
    else:
        resultado.delete()
    partido.estado = Partido.Estado.PROGRAMADO
    partido.save(update_fields=["estado", "actualizado_en"])
    tabla.recalcular(partido.campeonato)
    return anterior
