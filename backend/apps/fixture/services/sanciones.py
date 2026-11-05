"""
apps/fixture/services/sanciones.py
F3-08 — Ciclo tarjeta → sanción → cumplimiento (RF14, RF8).

* Una tarjeta roja suspende `SANCION_PARTIDOS_ROJA` partidos.
* Cada `AMARILLAS_PARA_SANCION` amarillas acumuladas en el campeonato suspenden 1 partido.
* La sanción se descuenta al finalizar cada partido posterior del equipo
  (no el partido en el que se originó). Un W.O. no cuenta como partido cumplido.
* `validar_elegibilidad` (deportes.services) informa las sanciones pendientes y
  las incidencias bloquean a un jugador sancionado.
"""
from django.conf import settings
from django.db.models import F

from apps.deportes.models import FichaJugador
from apps.fixture.models import Incidencia, Partido

TIPOS_CON_JUGADOR = (
    Incidencia.Tipo.GOL,
    Incidencia.Tipo.TARJETA_AMARILLA,
    Incidencia.Tipo.TARJETA_ROJA,
    Incidencia.Tipo.LESION,
)


def sancion_proviene_del_partido(ficha: FichaJugador, partido: Partido) -> bool:
    """¿La sanción vigente de la ficha se originó en una incidencia de este partido?"""
    if not ficha.sancion_origen:
        return False
    return Incidencia.objects.filter(pk=ficha.sancion_origen, partido=partido).exists()


def partidos_de_sancion(incidencia: Incidencia) -> int:
    """Partidos de suspensión que genera la incidencia (0 si no sanciona)."""
    if incidencia.jugador_id is None:
        return 0
    if incidencia.tipo == Incidencia.Tipo.TARJETA_ROJA:
        return settings.SANCION_PARTIDOS_ROJA
    if incidencia.tipo == Incidencia.Tipo.TARJETA_AMARILLA:
        limite = settings.AMARILLAS_PARA_SANCION
        amarillas = Incidencia.objects.filter(
            jugador_id=incidencia.jugador_id,
            tipo=Incidencia.Tipo.TARJETA_AMARILLA,
            partido__campeonato_id=incidencia.partido.campeonato_id,
        ).count()
        return 1 if limite > 0 and amarillas % limite == 0 else 0
    return 0


def aplicar_sancion(incidencia: Incidencia) -> int:
    """Suma la sanción de la incidencia a la ficha. Devuelve los partidos sumados."""
    partidos = partidos_de_sancion(incidencia)
    if partidos:
        FichaJugador.objects.filter(pk=incidencia.jugador_id).update(
            partidos_sancion_restantes=F("partidos_sancion_restantes") + partidos,
            sancion_origen=incidencia.pk,
        )
    return partidos


def descontar_sanciones(partido: Partido) -> int:
    """Descuenta 1 partido a los sancionados de ambos equipos. Devuelve fichas actualizadas."""
    actualizadas = 0
    for equipo_id in (partido.equipo_local_id, partido.equipo_visitante_id):
        if equipo_id is None:
            continue
        for ficha in FichaJugador.objects.filter(
            equipo_id=equipo_id, partidos_sancion_restantes__gt=0
        ):
            if sancion_proviene_del_partido(ficha, partido):
                continue
            ficha.partidos_sancion_restantes -= 1
            ficha.save(update_fields=["partidos_sancion_restantes"])
            actualizadas += 1
    return actualizadas
