"""F7-01 — Optimizador en modo reparación: reubica solo lo afectado y nunca rompe una regla dura."""
import pytest
from django.utils import timezone

from apps.agente.tests.helpers_agente import a_las, clima_caido, crear_partido, dia, escenario_en_curso, simular_clima
from apps.fixture.models import Partido
from apps.fixture.services.reparacion import proponer_reparacion
from apps.fixture.tests.helpers import hay_solapes
from apps.instalaciones.models import BloqueoCancha, HorarioCancha

pytestmark = pytest.mark.django_db


def propuesta_para(partidos, hasta=7, **kw):
    return proponer_reparacion(partidos, desde=dia(3), hasta=dia(3 + hasta), **kw)


def aplicar_en_memoria(propuesta):
    for c in propuesta.cambios:
        Partido.objects.filter(pk=c.partido.pk).update(cancha=c.cancha, fecha_hora=c.inicio, fecha_hora_fin=c.fin)
    return list(Partido.objects.all())


@pytest.fixture
def lluvia(monkeypatch):
    simular_clima(monkeypatch, dias_lluviosos=[3])


def test_los_partidos_al_aire_libre_salen_del_dia_de_lluvia_sin_chocar(lluvia):
    esc = escenario_en_curso(equipos=4, canchas=2)
    a = crear_partido(esc, esc.equipos[0], esc.equipos[1], esc.canchas[0], a_las(3, 16))
    b = crear_partido(esc, esc.equipos[2], esc.equipos[3], esc.canchas[1], a_las(3, 16))

    p = propuesta_para([a, b])

    assert len(p.cambios) == 2 and not p.sin_solucion and p.clima_verificado
    assert all(timezone.localtime(c.inicio).date() != dia(3) for c in p.cambios)         # ninguno queda en el día lluvioso
    assert all(c.clima in ("BAJO", "MEDIO") for c in p.cambios)
    assert hay_solapes(aplicar_en_memoria(p)) is None
    # Se mueve lo mínimo: al día siguiente y a la misma hora.
    assert {(timezone.localtime(c.inicio).date(), timezone.localtime(c.inicio).hour) for c in p.cambios} == {(dia(4), 16)}


def test_una_cancha_techada_no_sufre_la_lluvia_y_se_prefiere_el_mismo_horario(lluvia):
    esc = escenario_en_curso(equipos=2, canchas=2, techadas=1)
    abierta, techada = esc.canchas
    a = crear_partido(esc, esc.equipos[0], esc.equipos[1], abierta, a_las(3, 16))

    p = propuesta_para([a])

    (cambio,) = p.cambios
    assert cambio.cancha.pk == techada.pk and cambio.inicio == a.fecha_hora and cambio.desplazamiento_min == 0


def test_no_usa_horarios_ocupados_por_partidos_que_no_se_mueven(lluvia):
    esc = escenario_en_curso(equipos=4, canchas=1)
    a = crear_partido(esc, esc.equipos[0], esc.equipos[1], esc.canchas[0], a_las(3, 16))
    ocupa = crear_partido(esc, esc.equipos[2], esc.equipos[3], esc.canchas[0], a_las(4, 16), jornada=2)

    p = propuesta_para([a])

    (cambio,) = p.cambios
    assert not (cambio.inicio < ocupa.fecha_hora_fin and ocupa.fecha_hora < cambio.fin)
    assert hay_solapes(aplicar_en_memoria(p)) is None


def test_respeta_el_descanso_del_equipo_con_sus_otros_partidos(lluvia):
    esc = escenario_en_curso(equipos=4, canchas=2)
    a = crear_partido(esc, esc.equipos[0], esc.equipos[1], esc.canchas[0], a_las(3, 16))
    # El equipo 1 juega al día siguiente a las 16:00: a menos de 24 h no puede jugar otro partido.
    crear_partido(esc, esc.equipos[0], esc.equipos[2], esc.canchas[1], a_las(4, 16), jornada=2)

    (cambio,) = propuesta_para([a]).cambios

    # El otro partido termina el día 4 a las 17:30: 24 h de descanso después → desde el día 5 a las 17:30.
    assert cambio.inicio >= a_las(5, 17, 30)


def test_dos_partidos_del_mismo_equipo_reubicados_a_la_vez_respetan_el_descanso(lluvia):
    esc = escenario_en_curso(equipos=3, canchas=2)
    a = crear_partido(esc, esc.equipos[0], esc.equipos[1], esc.canchas[0], a_las(3, 10))
    b = crear_partido(esc, esc.equipos[0], esc.equipos[2], esc.canchas[1], a_las(3, 18), jornada=2)

    p = propuesta_para([a, b], hasta=8)

    assert len(p.cambios) == 2
    iniciales = sorted(c.inicio for c in p.cambios)
    assert (iniciales[1] - iniciales[0]).total_seconds() >= 24 * 3600 + 90 * 60 - 1


def test_un_bloqueo_de_cancha_se_respeta(lluvia):
    esc = escenario_en_curso(equipos=2, canchas=1)
    a = crear_partido(esc, esc.equipos[0], esc.equipos[1], esc.canchas[0], a_las(3, 16))
    BloqueoCancha.objects.create(cancha=esc.canchas[0], fecha_inicio=a_las(4, 0), fecha_fin=a_las(5, 0), motivo="Mantenimiento")

    (cambio,) = propuesta_para([a]).cambios

    assert timezone.localtime(cambio.inicio).date() >= dia(5)


def test_sin_horarios_libres_se_explica_en_vez_de_inventar(lluvia):
    esc = escenario_en_curso(equipos=2, canchas=1)
    a = crear_partido(esc, esc.equipos[0], esc.equipos[1], esc.canchas[0], a_las(3, 16))
    HorarioCancha.objects.filter(cancha=esc.canchas[0]).delete()

    p = propuesta_para([a])

    assert not p.cambios and len(p.sin_solucion) == 1
    assert "horario libre" in p.sin_solucion[0][1]


def test_solo_se_reubican_partidos_programados_de_campeonatos_en_curso(lluvia):
    esc = escenario_en_curso(equipos=4, canchas=2)
    jugado = crear_partido(esc, esc.equipos[0], esc.equipos[1], esc.canchas[0], a_las(3, 16), estado=Partido.Estado.FINALIZADO)
    suspendido = crear_partido(esc, esc.equipos[2], esc.equipos[3], esc.canchas[1], a_las(3, 16), jornada=2, estado=Partido.Estado.SUSPENDIDO)

    p = propuesta_para([jugado, suspendido])

    assert not p.cambios and len(p.descartados) == 2


def test_si_el_clima_no_responde_se_propone_igual_y_se_avisa(monkeypatch):
    clima_caido(monkeypatch)
    esc = escenario_en_curso(equipos=2, canchas=2)
    a = crear_partido(esc, esc.equipos[0], esc.equipos[1], esc.canchas[0], a_las(3, 16))

    p = propuesta_para([a])

    assert len(p.cambios) == 1 and p.clima_verificado is False and p.cambios[0].clima is None


def test_no_propone_horarios_con_menos_de_la_antelacion_minima(lluvia, settings):
    settings.AGENTE_ANTELACION_HORAS = 48
    esc = escenario_en_curso(equipos=2, canchas=2)
    a = crear_partido(esc, esc.equipos[0], esc.equipos[1], esc.canchas[0], a_las(3, 16))
    ahora = a_las(3, 12)

    (cambio,) = proponer_reparacion([a], desde=dia(3), hasta=dia(8), ahora=ahora).cambios

    assert cambio.inicio >= ahora + (a_las(1, 0) - a_las(0, 0)) * 2
