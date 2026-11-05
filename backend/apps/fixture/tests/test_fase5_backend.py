"""Fase 5 — soporte de backend para los paneles: estadísticas públicas, filtro por equipo y reportes."""
import io

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.auditoria.models import Bitacora
from apps.deportes.models import Campeonato
from apps.fixture.models import Incidencia
from apps.fixture.services.fixture_generator import FixtureGenerator
from apps.users.models import Usuario

from .helpers import cliente_de, crear_escenario, crear_jugador, crear_usuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def liga():
    esc = crear_escenario(equipos=3, canchas=2)
    esc.partidos = list(FixtureGenerator(esc.campeonato.pk).generar())
    # El fixture se publica (visible al público) cuando el campeonato inicia.
    Campeonato.objects.filter(pk=esc.campeonato.pk).update(estado=Campeonato.Estado.EN_CURSO)
    return esc


def registrar_gol(esc, partido, jugador):
    return esc.client.post(
        reverse("partido-registrar-incidencia", kwargs={"pk": partido.pk}),
        {"tipo": "GOL", "jugador": jugador.pk, "minuto": 10},
        format="json",
    )


def resultado(esc, partido, local, visitante):
    return esc.client.post(
        reverse("partido-registrar-resultado", kwargs={"pk": partido.pk}),
        {"goles_local": local, "goles_visitante": visitante},
        format="json",
    )


def test_estadisticas_son_publicas_y_calculan_goleadores_y_tarjetas(liga):
    p = liga.partidos[0]
    goleador = crear_jugador(p.equipo_local, 9)
    rival = crear_jugador(p.equipo_visitante, 4)
    for _ in range(2):
        assert registrar_gol(liga, p, goleador).status_code == 201
    assert registrar_gol(liga, p, rival).status_code == 201
    liga.client.post(
        reverse("partido-registrar-incidencia", kwargs={"pk": p.pk}),
        {"tipo": "TARJETA_AMARILLA", "jugador": rival.pk}, format="json",
    )
    assert resultado(liga, p, 2, 1).status_code == 201

    anonimo = APIClient().get(reverse("fixture-estadisticas"), {"campeonato": liga.campeonato.pk})

    assert anonimo.status_code == 200
    datos = anonimo.data
    assert datos["resumen"]["partidos_jugados"] == 1
    assert datos["resumen"]["goles"] == 3
    assert datos["resumen"]["victorias_local"] == 1
    assert datos["goleadores"][0]["goles"] == 2
    assert datos["goleadores"][0]["jugador"] == f"{goleador.nombre} {goleador.apellido}"
    assert datos["tarjetas"][0]["amarillas"] == 1
    assert datos["mejor_ataque"]["goles"] == 2
    assert "carnet" not in str(datos)


def test_estadisticas_validan_parametro_y_existencia():
    cliente = APIClient()
    assert cliente.get(reverse("fixture-estadisticas")).status_code == 400
    assert cliente.get(reverse("fixture-estadisticas"), {"campeonato": 999999}).status_code == 404


def test_estadisticas_vacias_no_fallan(liga):
    datos = APIClient().get(reverse("fixture-estadisticas"), {"campeonato": liga.campeonato.pk}).data

    assert datos["resumen"]["partidos_jugados"] == 0
    assert datos["goleadores"] == [] and datos["mejor_ataque"] is None


def test_filtro_de_partidos_por_equipo(liga):
    equipo = liga.equipos[0]

    respuesta = APIClient().get(reverse("partido-list"), {"equipo": equipo.pk})

    assert respuesta.status_code == 200
    assert respuesta.data["count"] == 2  # en una liga de 3 juega 2 partidos
    assert APIClient().get(reverse("partido-list"), {"equipo": "x"}).data["count"] == 3


def test_incidencia_expone_nombre_del_jugador(liga):
    p = liga.partidos[0]
    jugador = crear_jugador(p.equipo_local, 7)

    respuesta = registrar_gol(liga, p, jugador)

    assert respuesta.data["jugador_nombre"] == f"{jugador.nombre} {jugador.apellido}"
    assert respuesta.data["equipo_id"] == p.equipo_local_id
    detalle = APIClient().get(reverse("partido-detail", kwargs={"pk": p.pk}))
    assert detalle.data["incidencias"][0]["jugador_nombre"]
    assert Incidencia.objects.count() == 1


@pytest.mark.parametrize("formato", ["pdf", "excel"])
def test_reporte_de_equipo_y_jugador_se_descarga_y_se_audita(liga, formato):
    p = liga.partidos[0]
    jugador = crear_jugador(p.equipo_local, 11)
    registrar_gol(liga, p, jugador)

    equipo = liga.client_org.get(reverse(f"reporte-equipo-{formato}", kwargs={"equipo_id": p.equipo_local_id}))
    ficha = liga.client.get(reverse(f"reporte-jugador-{formato}", kwargs={"jugador_id": jugador.pk}))

    esperado = "application/pdf" if formato == "pdf" else "spreadsheetml"
    for respuesta in (equipo, ficha):
        assert respuesta.status_code == 200
        assert esperado in respuesta["Content-Type"]
        assert "attachment" in respuesta["Content-Disposition"]
    assert Bitacora.objects.filter(accion=Bitacora.Accion.EXPORTAR, modulo="equipo").exists()
    assert Bitacora.objects.filter(accion=Bitacora.Accion.EXPORTAR, modulo="jugador").exists()
    if formato == "excel":
        import openpyxl
        libro = openpyxl.load_workbook(io.BytesIO(ficha.content))
        valores = [c.value for fila in libro["Resumen"].iter_rows() for c in fila]
        assert "Goles" in valores and 1 in valores


def test_reportes_por_equipo_y_jugador_exigen_gestion(liga):
    delegado = cliente_de(crear_usuario(Usuario.Rol.DELEGADO, liga.equipos[0].facultad))
    urls = [
        reverse("reporte-equipo-pdf", kwargs={"equipo_id": liga.equipos[0].pk}),
        reverse("reporte-jugador-excel", kwargs={"jugador_id": 1}),
    ]
    for url in urls:
        assert APIClient().get(url).status_code == 401
        assert delegado.get(url).status_code == 403


def test_reportes_inexistentes_devuelven_404(liga):
    assert liga.client.get(reverse("reporte-equipo-pdf", kwargs={"equipo_id": 999999})).status_code == 404
    assert liga.client.get(reverse("reporte-jugador-pdf", kwargs={"jugador_id": 999999})).status_code == 404


def test_paginacion_acepta_page_size_y_limita_el_maximo():
    esc = crear_escenario(equipos=2, canchas=1)
    for _ in range(25):
        crear_escenario(equipos=0, canchas=0)

    por_defecto = APIClient().get(reverse("campeonato-list"))
    amplia = APIClient().get(reverse("campeonato-list"), {"page_size": 100})
    excesiva = APIClient().get(reverse("campeonato-list"), {"page_size": 5000})

    assert len(por_defecto.data["results"]) == 20
    assert len(amplia.data["results"]) == 26
    assert len(excesiva.data["results"]) == 26 and esc.campeonato.pk


def test_borrar_un_registro_en_uso_devuelve_409_claro():
    esc = crear_escenario(equipos=0, canchas=0)

    # La categoría está protegida por el campeonato que la usa.
    respuesta = esc.client.delete(
        reverse("categoria-detail", kwargs={"pk": esc.campeonato.categoria_id})
    )

    assert respuesta.status_code == 409
    assert "en uso" in respuesta.data["detail"]


def test_queja_expone_el_detalle_del_partido(liga):
    from apps.quejas.models import Queja

    p = liga.partidos[0]
    queja = Queja.objects.create(
        tipo="QUEJA", descripcion="Reclamo", encuentro=p, delegado=p.equipo_local.delegado
    )

    respuesta = liga.client.get(reverse("queja-detail", kwargs={"pk": queja.pk}))

    assert respuesta.status_code == 200
    assert respuesta.data["encuentro_detalle"]["local"] == p.equipo_local.nombre
    assert respuesta.data["encuentro_detalle"]["campeonato"] == liga.campeonato.nombre
    assert respuesta.data["delegado_nombre"]
