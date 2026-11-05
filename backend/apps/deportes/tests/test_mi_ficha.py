"""F7-10 — Panel del jugador: solo lectura de su propia ficha."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.deportes.models import Campeonato
from apps.fixture.models import Incidencia, Partido, Resultado
from apps.fixture.tests.helpers import cliente_de, crear_escenario, crear_jugador, crear_usuario
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db
URL = "/api/v1/deportes/mi-ficha/"


@pytest.fixture
def mundo():
    esc = crear_escenario(equipos=2, canchas=1, estado=Campeonato.Estado.EN_CURSO)
    local, visitante = esc.equipos
    cuenta = crear_usuario(Usuario.Rol.JUGADOR)
    ficha = crear_jugador(local, 9)
    ficha.usuario = cuenta
    ficha.partidos_sancion_restantes = 2
    ficha.save(update_fields=["usuario", "partidos_sancion_restantes"])
    ajeno = crear_jugador(visitante, 7)                       # otra persona: no debe verse
    jugado = Partido.objects.create(campeonato=esc.campeonato, equipo_local=local, equipo_visitante=visitante, jornada=1, duracion_min=90,
                                    fecha_hora=timezone.now() - timedelta(days=3), estado=Partido.Estado.FINALIZADO)
    Resultado.objects.create(partido=jugado, goles_local=2, goles_visitante=1)
    Incidencia.objects.create(partido=jugado, tipo="GOL", jugador=ficha, minuto=10)
    Incidencia.objects.create(partido=jugado, tipo="TARJETA_AMARILLA", jugador=ficha, minuto=50)
    Partido.objects.create(campeonato=esc.campeonato, equipo_local=visitante, equipo_visitante=local, jornada=2, duracion_min=90,
                           fecha_hora=timezone.now() + timedelta(days=4))
    esc.cuenta, esc.ficha, esc.ajeno = cuenta, ficha, ajeno
    return esc


def test_el_jugador_ve_su_ficha_estadisticas_sancion_y_partidos(mundo):
    r = cliente_de(mundo.cuenta).get(URL)

    assert r.status_code == 200 and len(r.data["fichas"]) == 1
    f = r.data["fichas"][0]
    assert f["numero"] == 9 and f["equipo"]["nombre"] == mundo.equipos[0].nombre
    assert f["estadisticas"]["goles"] == 1 and f["estadisticas"]["amarillas"] == 1
    assert f["sancion"]["partidos_restantes"] == 2 and "Suspendido" in f["sancion"]["mensaje"]
    assert f["ultimos_resultados"][0]["marcador"] == "2-1" and f["ultimos_resultados"][0]["resultado"] == "G"
    assert len(f["proximos_partidos"]) == 1 and f["proximos_partidos"][0]["es_local"] is False


def test_solo_ve_sus_propias_fichas_y_sin_ficha_la_lista_va_vacia(mundo):
    otra_cuenta = crear_usuario(Usuario.Rol.JUGADOR)
    assert cliente_de(otra_cuenta).get(URL).data == {"fichas": []}
    assert all(f["id"] != mundo.ajeno.pk for f in cliente_de(mundo.cuenta).get(URL).data["fichas"])


def test_otros_roles_y_visitantes_no_entran(mundo):
    assert APIClient().get(URL).status_code == 401
    for rol in (Usuario.Rol.DELEGADO, Usuario.Rol.ORGANIZADOR, Usuario.Rol.ADMIN_DUBSS):
        assert cliente_de(crear_usuario(rol)).get(URL).status_code == 403


def test_el_jugador_sigue_sin_permisos_de_escritura(mundo):
    c = cliente_de(mundo.cuenta)
    partido = Partido.objects.first()
    assert c.post(f"/api/v1/fixture/partidos/{partido.pk}/incidencia/", {"tipo": "GOL"}, format="json").status_code == 403
    assert c.post("/api/v1/deportes/equipos/", {"nombre": "x"}, format="json").status_code == 403
