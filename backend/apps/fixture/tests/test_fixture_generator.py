"""F3-03 — Generador de fixture robusto (RF11 base)."""
import time
from datetime import datetime, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.deportes.models import Campeonato, RestriccionHorarioFacultad
from apps.fixture.models import Partido, TablaPosiciones
from apps.fixture.services.fixture_generator import (
    FixtureConflicto, FixtureError, FixtureGenerator,
)
from apps.instalaciones.models import BloqueoCancha, HorarioCancha

from .helpers import crear_escenario, hay_solapes

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("n_equipos", [4, 5, 8])
def test_liga_sin_solapes_y_con_todos_los_enfrentamientos(n_equipos):
    esc = crear_escenario(equipos=n_equipos, canchas=2)

    partidos = FixtureGenerator(esc.campeonato.pk).generar()

    assert len(partidos) == n_equipos * (n_equipos - 1) // 2
    assert hay_solapes(Partido.objects.filter(campeonato=esc.campeonato)) is None
    parejas = {frozenset((p.equipo_local_id, p.equipo_visitante_id)) for p in partidos}
    assert len(parejas) == len(partidos)  # nadie juega dos veces contra el mismo rival
    assert all(p.generado_por_ml is False for p in partidos)
    assert all(timezone.is_aware(p.fecha_hora) for p in partidos)
    # La tabla queda inicializada para todos los equipos.
    assert TablaPosiciones.objects.filter(campeonato=esc.campeonato).count() == n_equipos


def test_veinte_equipos_se_generan_en_menos_de_10_segundos_sin_conflictos():
    esc = crear_escenario(equipos=20, canchas=3)

    inicio = time.perf_counter()
    partidos = FixtureGenerator(esc.campeonato.pk).generar()
    duracion = time.perf_counter() - inicio

    assert len(partidos) == 190
    assert hay_solapes(Partido.objects.filter(campeonato=esc.campeonato)) is None
    assert duracion < 10, f"El fixture de 20 equipos tardó {duracion:.1f} s (RNF04)."


def test_programa_en_paralelo_por_cancha():
    esc = crear_escenario(equipos=4, canchas=2)

    FixtureGenerator(esc.campeonato.pk).generar()

    primera_jornada = Partido.objects.filter(campeonato=esc.campeonato, jornada=1)
    assert primera_jornada.count() == 2
    assert len({p.fecha_hora for p in primera_jornada}) == 1  # mismo horario...
    assert len({p.cancha_id for p in primera_jornada}) == 2   # ...en canchas distintas


def test_equipo_impar_descansa_cada_jornada():
    esc = crear_escenario(equipos=5, canchas=2)

    FixtureGenerator(esc.campeonato.pk).generar()

    for jornada in range(1, 6):
        partidos = Partido.objects.filter(campeonato=esc.campeonato, jornada=jornada)
        assert partidos.count() == 2
        jugando = {e for p in partidos for e in (p.equipo_local_id, p.equipo_visitante_id)}
        assert len(jugando) == 4  # el quinto equipo descansa


def test_doble_vuelta_invierte_localia():
    esc = crear_escenario(equipos=4, canchas=2)

    partidos = FixtureGenerator(esc.campeonato.pk, doble_vuelta=True).generar()

    assert len(partidos) == 12
    ida = {(p.equipo_local_id, p.equipo_visitante_id) for p in partidos if p.jornada <= 3}
    vuelta = {(p.equipo_local_id, p.equipo_visitante_id) for p in partidos if p.jornada > 3}
    assert vuelta == {(v, l) for l, v in ida}
    assert max(p.jornada for p in partidos) == 6


def test_no_pasa_de_medianoche_y_respeta_el_horario_de_la_cancha():
    esc = crear_escenario(equipos=8, canchas=1)

    partidos = FixtureGenerator(esc.campeonato.pk).generar()

    for p in partidos:
        inicio, fin = timezone.localtime(p.fecha_hora), timezone.localtime(p.fecha_hora_fin)
        assert inicio.date() == fin.date()
        assert inicio.time() >= datetime.strptime("08:00", "%H:%M").time()
        assert fin.time() <= datetime.strptime("22:00", "%H:%M").time()


def test_respeta_bloqueos_de_cancha():
    esc = crear_escenario(equipos=2, canchas=1)
    dia = esc.campeonato.fecha_inicio
    bloqueo_inicio = timezone.make_aware(datetime.combine(dia, datetime.min.time())) \
        + timedelta(hours=8)
    BloqueoCancha.objects.create(
        cancha=esc.canchas[0],
        fecha_inicio=bloqueo_inicio,
        fecha_fin=bloqueo_inicio + timedelta(hours=4),
        tipo=BloqueoCancha.Tipo.MANTENIMIENTO,
        motivo="Pintura",
    )

    (partido,) = FixtureGenerator(esc.campeonato.pk).generar()

    assert timezone.localtime(partido.fecha_hora).hour >= 12


def test_respeta_restricciones_de_facultad():
    esc = crear_escenario(equipos=2, canchas=1)
    RestriccionHorarioFacultad.objects.create(
        facultad=esc.equipos[0].facultad,
        dia_semana=esc.campeonato.fecha_inicio.weekday(),
        hora_inicio="08:00",
        hora_fin="12:00",
        motivo="Clases",
    )

    (partido,) = FixtureGenerator(esc.campeonato.pk).generar()

    assert timezone.localtime(partido.fecha_hora).hour >= 12


def test_dos_campeonatos_comparten_canchas_sin_solaparse():
    esc1 = crear_escenario(equipos=4, canchas=1)
    esc2 = crear_escenario(equipos=4, canchas=0, deporte=esc1.deporte)

    FixtureGenerator(esc1.campeonato.pk).generar()
    FixtureGenerator(esc2.campeonato.pk).generar()

    assert hay_solapes(Partido.objects.all()) is None
    assert Partido.objects.count() == 12


def test_un_equipo_no_juega_a_la_vez_en_dos_campeonatos():
    esc1 = crear_escenario(equipos=2, canchas=2)
    esc2 = crear_escenario(equipos=0, canchas=0, deporte=esc1.deporte)
    from apps.deportes.models import Inscripcion
    Inscripcion.objects.create(
        campeonato=esc2.campeonato, equipo=esc1.equipos[0],
        estado=Inscripcion.Estado.APROBADA,
    )
    Inscripcion.objects.create(
        campeonato=esc2.campeonato, equipo=esc1.equipos[1],
        estado=Inscripcion.Estado.APROBADA,
    )

    FixtureGenerator(esc1.campeonato.pk).generar()
    FixtureGenerator(esc2.campeonato.pk).generar()

    assert hay_solapes(Partido.objects.all()) is None


def test_regenerar_reemplaza_los_partidos_pendientes():
    esc = crear_escenario(equipos=4, canchas=2)
    FixtureGenerator(esc.campeonato.pk).generar()
    ids_anteriores = set(Partido.objects.values_list("pk", flat=True))

    FixtureGenerator(esc.campeonato.pk, dias_entre_jornadas=3).generar()

    assert Partido.objects.filter(campeonato=esc.campeonato).count() == 6
    assert not ids_anteriores & set(Partido.objects.values_list("pk", flat=True))


@pytest.mark.parametrize(
    "estado", [Partido.Estado.FINALIZADO, Partido.Estado.WALKOVER, Partido.Estado.EN_CURSO]
)
def test_no_borra_partidos_jugados_ni_en_curso(estado):
    esc = crear_escenario(equipos=4, canchas=2)
    FixtureGenerator(esc.campeonato.pk).generar()
    jugado = Partido.objects.filter(campeonato=esc.campeonato).first()
    Partido.objects.filter(pk=jugado.pk).update(estado=estado)
    antes = Partido.objects.filter(campeonato=esc.campeonato).count()

    with pytest.raises(FixtureConflicto) as error:
        FixtureGenerator(esc.campeonato.pk).generar()

    assert "no se puede regenerar" in str(error.value)
    assert Partido.objects.filter(campeonato=esc.campeonato).count() == antes


def test_borrado_y_creacion_son_atomicos():
    esc = crear_escenario(equipos=4, canchas=2)
    FixtureGenerator(esc.campeonato.pk).generar()
    ids = set(Partido.objects.values_list("pk", flat=True))
    HorarioCancha.objects.all().delete()  # ahora no se podrá programar nada

    with pytest.raises(FixtureError):
        FixtureGenerator(esc.campeonato.pk).generar()

    assert set(Partido.objects.values_list("pk", flat=True)) == ids  # el fixture previo sigue


def test_sin_disponibilidad_falla_con_error_descriptivo_y_sin_bucles():
    esc = crear_escenario(equipos=2, canchas=1)
    HorarioCancha.objects.all().delete()

    inicio = time.perf_counter()
    with pytest.raises(FixtureError) as error:
        FixtureGenerator(esc.campeonato.pk).generar()

    assert "No hay cancha y horario disponibles" in str(error.value)
    assert time.perf_counter() - inicio < 5


@pytest.mark.parametrize("estado", [
    Campeonato.Estado.PLANIFICACION, Campeonato.Estado.INSCRIPCIONES, Campeonato.Estado.EN_CURSO,
    Campeonato.Estado.FINALIZADO, Campeonato.Estado.CANCELADO,
])
def test_solo_se_genera_fixture_con_las_inscripciones_cerradas(estado):
    esc = crear_escenario(equipos=2, canchas=1, estado=estado)

    with pytest.raises(FixtureError, match="Cierra las inscripciones"):
        FixtureGenerator(esc.campeonato.pk).generar()


def test_exige_dos_equipos_y_canchas():
    esc = crear_escenario(equipos=1, canchas=1)
    with pytest.raises(FixtureError, match="al menos 2 equipos"):
        FixtureGenerator(esc.campeonato.pk).generar()
    esc = crear_escenario(equipos=2, canchas=0)
    with pytest.raises(FixtureError, match="canchas activas"):
        FixtureGenerator(esc.campeonato.pk).generar()


def test_solo_equipos_con_inscripcion_aprobada_entran_al_fixture():
    from apps.deportes.models import Inscripcion
    from .helpers import crear_equipo

    esc = crear_escenario(equipos=3, canchas=1)
    pendiente = crear_equipo("Pendiente", esc.campeonato, Inscripcion.Estado.PENDIENTE)
    rechazado = crear_equipo("Rechazado", esc.campeonato, Inscripcion.Estado.RECHAZADA)

    partidos = FixtureGenerator(esc.campeonato.pk).generar()

    jugando = {e for p in partidos for e in (p.equipo_local_id, p.equipo_visitante_id)}
    assert pendiente.pk not in jugando and rechazado.pk not in jugando
    assert len(partidos) == 3


def test_el_ml_es_opcional_el_metodo_base_nunca_marca_generado_por_ml():
    esc = crear_escenario(equipos=4, canchas=2)

    gen = FixtureGenerator(esc.campeonato.pk)
    partidos = gen.generar()

    assert not any(p.generado_por_ml for p in partidos)
    assert gen.resultado["generado_por_ml"] is False and gen.resultado["ml"] is None


def test_parametros_invalidos():
    esc = crear_escenario(equipos=2, canchas=1)
    with pytest.raises(FixtureError, match="HH:MM"):
        FixtureGenerator(esc.campeonato.pk, hora_inicio="mañana")
    with pytest.raises(FixtureError, match="al menos 1"):
        FixtureGenerator(esc.campeonato.pk, dias_entre_jornadas=0)
    with pytest.raises(FixtureError, match="no existe"):
        FixtureGenerator(999999)


# ── Vía API ───────────────────────────────────────────────────────────────────

def test_api_genera_fixture_y_registra_en_bitacora():
    from apps.auditoria.models import Bitacora

    esc = crear_escenario(equipos=4, canchas=2)

    respuesta = esc.client.post(
        reverse("fixture-generar"),
        {"campeonato_id": esc.campeonato.pk, "hora_inicio": "09:00", "doble_vuelta": True},
        format="json",
    )

    assert respuesta.status_code == 201
    assert respuesta.data["total_partidos"] == 12
    assert respuesta.data["generado_por_ml"] is False
    registro = Bitacora.objects.get(accion=Bitacora.Accion.GENERAR_FIXTURE)
    assert registro.detalle["cantidad_partidos"] == 12


def test_api_responde_409_si_hay_partidos_jugados():
    esc = crear_escenario(equipos=4, canchas=2)
    FixtureGenerator(esc.campeonato.pk).generar()
    Partido.objects.filter(campeonato=esc.campeonato).update(estado=Partido.Estado.FINALIZADO)

    respuesta = esc.client.post(
        reverse("fixture-generar"), {"campeonato_id": esc.campeonato.pk}, format="json"
    )

    assert respuesta.status_code == 409
    assert "no se puede regenerar" in respuesta.data["error"]


@pytest.mark.parametrize(
    "cuerpo",
    [
        {},
        {"campeonato_id": "abc"},
        {"campeonato_id": 1, "dias_entre_jornadas": "x"},
        {"campeonato_id": 1, "hora_inicio": "9am"},
    ],
)
def test_api_valida_parametros_con_400(cuerpo):
    esc = crear_escenario(equipos=2, canchas=1)

    respuesta = esc.client.post(reverse("fixture-generar"), cuerpo, format="json")

    assert respuesta.status_code == 400


def test_el_fixture_generado_no_tiene_conflictos_segun_la_validacion_oficial():
    """Contrasta la lógica en memoria del generador con `detectar_conflictos`."""
    from apps.fixture.services.programacion import detectar_conflictos

    esc = crear_escenario(equipos=8, canchas=2)
    RestriccionHorarioFacultad.objects.create(
        facultad=esc.equipos[0].facultad,
        dia_semana=esc.campeonato.fecha_inicio.weekday(),
        hora_inicio="08:00",
        hora_fin="10:00",
        motivo="Clases",
    )
    FixtureGenerator(esc.campeonato.pk).generar()

    for p in Partido.objects.filter(campeonato=esc.campeonato).select_related(
        "cancha", "equipo_local", "equipo_visitante"
    ):
        assert detectar_conflictos(
            cancha=p.cancha, fecha_hora=p.fecha_hora, duracion_min=p.duracion_min,
            equipo_local=p.equipo_local, equipo_visitante=p.equipo_visitante,
            partido_id=p.pk,
        ) == []
