"""Pruebas de auditoría de acciones deportivas, reportes y accesos denegados."""
from datetime import date
from types import SimpleNamespace

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auditoria.models import Bitacora
from apps.deportes.models import (
    Campeonato, Categoria, Deporte, Equipo, Facultad, Inscripcion,
)
from apps.fixture.models import Incidencia, Partido
from apps.ml.models import PrediccionPartido, RiesgoClimatico
from apps.users.models import Usuario


pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def admin(db):
    return Usuario.objects.create_user(
        email="admin-nucleo@uagrm.edu.bo",
        password="AdminPass123!",
        nombre="Admin",
        apellido="Nucleo",
        rol=Usuario.Rol.ADMIN_DUBSS,
    )


@pytest.fixture
def campeonato(db, admin):
    deporte = Deporte.objects.create(nombre="Futbol auditoria")
    categoria = Categoria.objects.create(deporte=deporte, nombre="Primera")
    return Campeonato.objects.create(
        nombre="Campeonato auditoria",
        categoria=categoria,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
        creado_por=admin,
    )


@pytest.fixture
def equipos(campeonato):
    facultad_a = Facultad.objects.create(nombre="Facultad A", sigla="FA")
    facultad_b = Facultad.objects.create(nombre="Facultad B", sigla="FB")
    equipo_local = Equipo.objects.create(
        nombre="Local",
        facultad=facultad_a,
    )
    equipo_visitante = Equipo.objects.create(
        nombre="Visitante",
        facultad=facultad_b,
    )
    Inscripcion.objects.create(
        campeonato=campeonato,
        equipo=equipo_local,
        estado=Inscripcion.Estado.APROBADA,
    )
    Inscripcion.objects.create(
        campeonato=campeonato,
        equipo=equipo_visitante,
        estado=Inscripcion.Estado.APROBADA,
    )
    return (
        equipo_local,
        equipo_visitante,
    )


@pytest.fixture
def partido(campeonato, equipos):
    return Partido.objects.create(
        campeonato=campeonato,
        equipo_local=equipos[0],
        equipo_visitante=equipos[1],
        fecha_hora=timezone.now(),
    )


def test_403_autenticado_se_audita_con_metodo_y_ruta(client, db):
    usuario = Usuario.objects.create_user(
        email="sin-permiso@uagrm.edu.bo",
        password="UsuarioPass123!",
        nombre="Sin",
        apellido="Permiso",
        rol=Usuario.Rol.JUGADOR,
    )
    client.force_authenticate(user=usuario)

    respuesta = client.get(reverse("auditoria-bitacora"))

    assert respuesta.status_code == 403
    registro = Bitacora.objects.get(accion=Bitacora.Accion.ACCESO_DENEGADO)
    assert registro.usuario == usuario
    assert registro.resultado == Bitacora.Resultado.DENEGADO
    assert registro.detalle == {
        "metodo": "GET",
        "ruta": reverse("auditoria-bitacora"),
    }


def test_401_anonimo_no_se_registra_como_acceso_denegado(client):
    respuesta = client.get(reverse("auditoria-bitacora"))

    assert respuesta.status_code == 401
    assert not Bitacora.objects.filter(
        accion=Bitacora.Accion.ACCESO_DENEGADO
    ).exists()


def test_cambio_estado_campeonato_registra_estado_anterior_y_nuevo(
    client, admin, campeonato
):
    client.force_authenticate(user=admin)

    respuesta = client.patch(
        reverse("campeonato-cambiar-estado", kwargs={"pk": campeonato.pk}),
        {"estado": Campeonato.Estado.INSCRIPCIONES},
        format="json",
    )

    assert respuesta.status_code == 200
    registro = Bitacora.objects.get(accion=Bitacora.Accion.CAMBIO_ESTADO)
    assert registro.usuario == admin
    assert registro.modulo == "campeonato"
    assert registro.objeto_id == campeonato.pk
    assert registro.detalle == {
        "anterior": Campeonato.Estado.PLANIFICACION,
        "nuevo": Campeonato.Estado.INSCRIPCIONES,
    }


def test_generar_fixture_audita_creados_y_eliminados(
    client, admin, campeonato, partido, monkeypatch
):
    client.force_authenticate(user=admin)
    monkeypatch.setattr(
        "apps.fixture.views.FixtureGenerator",
        lambda **kwargs: SimpleNamespace(generar=lambda usar_ml=False, sembrar_con_ml=False: [partido]),
    )

    respuesta = client.post(
        reverse("fixture-generar"),
        {"campeonato_id": campeonato.pk},
        format="json",
    )

    assert respuesta.status_code == 201
    registro = Bitacora.objects.get(accion=Bitacora.Accion.GENERAR_FIXTURE)
    assert registro.usuario == admin
    assert registro.objeto_id == campeonato.pk
    assert registro.detalle == {
        "operacion": "generar",
        "cantidad_partidos": 1,
        "partidos_eliminados": 1,
        "doble_vuelta": False,
        "generado_por_ml": False,
    }


def test_eliminar_partido_audita_eliminacion_del_fixture(client, admin, partido):
    client.force_authenticate(user=admin)

    respuesta = client.delete(
        reverse("partido-detail", kwargs={"pk": partido.pk})
    )

    assert respuesta.status_code == 204
    registro = Bitacora.objects.get(accion=Bitacora.Accion.GENERAR_FIXTURE)
    assert registro.usuario == admin
    assert registro.objeto_id == partido.campeonato_id
    assert registro.detalle == {
        "operacion": "eliminar",
        "cantidad_partidos": 1,
    }


def test_registrar_resultado_audita_goles(client, admin, partido):
    client.force_authenticate(user=admin)

    respuesta = client.post(
        reverse("partido-registrar-resultado", kwargs={"pk": partido.pk}),
        {
            "partido": partido.pk,
            "goles_local": 2,
            "goles_visitante": 1,
        },
        format="json",
    )

    assert respuesta.status_code == 201
    registro = Bitacora.objects.get(accion=Bitacora.Accion.REGISTRAR_RESULTADO)
    assert registro.usuario == admin
    assert registro.modulo == "partido"
    assert registro.objeto_id == partido.pk
    assert registro.detalle == {
        "goles_local": 2, "goles_visitante": 1, "walkover": False,
    }


def test_registrar_incidencia_audita_tipo_y_minuto(client, admin, partido):
    client.force_authenticate(user=admin)

    respuesta = client.post(
        reverse("partido-registrar-incidencia", kwargs={"pk": partido.pk}),
        {
            "tipo": Incidencia.Tipo.OTRO,
            "minuto": 12,
        },
        format="json",
    )

    assert respuesta.status_code == 201
    incidencia = Incidencia.objects.get(partido=partido)
    registro = Bitacora.objects.get(accion=Bitacora.Accion.REGISTRAR_INCIDENCIA)
    assert registro.usuario == admin
    assert registro.objeto_id == partido.pk
    assert registro.detalle == {
        "tipo": Incidencia.Tipo.OTRO,
        "minuto": 12,
        "incidencia_id": incidencia.pk,
        "partidos_sancion": 0,
    }


@pytest.mark.parametrize(
    ("nombre_url", "formato"),
    [("reporte-pdf", "PDF"), ("reporte-excel", "Excel")],
)
def test_exportacion_de_reporte_audita_formato(
    client, admin, campeonato, nombre_url, formato, caplog
):
    client.force_authenticate(user=admin)
    with caplog.at_level("INFO", logger="apps.reportes.views"):
        respuesta = client.get(
            reverse(nombre_url, kwargs={"campeonato_id": campeonato.pk})
        )

    assert respuesta.status_code == 200
    assert not Bitacora.objects.filter(accion=Bitacora.Accion.EXPORTAR).exists()
    assert any(
        entrada.message == "Reporte de campeonato exportado."
        and entrada.__dict__["formato"] == formato
        for entrada in caplog.records
    )


def test_get_prediccion_de_partido_no_escribe_en_bitacora(
    client, admin, partido, monkeypatch
):
    client.force_authenticate(user=admin)
    prediccion = PrediccionPartido.objects.create(
        partido=partido,
        prob_victoria_local=0.6,
        prob_empate=0.2,
        prob_victoria_visit=0.2,
        goles_local_pred=2,
        goles_visit_pred=1,
        confianza=0.6,
    )
    monkeypatch.setattr(
        "apps.ml.views.PredictorResultados",
        lambda: SimpleNamespace(
            predecir=lambda partido, *, persistir: prediccion
        ),
    )

    respuesta = client.get(
        reverse("ml-prediccion", kwargs={"partido_id": partido.pk})
    )

    assert respuesta.status_code == 200
    assert not Bitacora.objects.filter(accion=Bitacora.Accion.ML_PRED).exists()


def test_get_tablero_de_predicciones_no_escribe_en_bitacora(
    client, admin, partido
):
    client.force_authenticate(user=admin)
    partido.estado = Partido.Estado.PROGRAMADO
    partido.save(update_fields=["estado"])
    PrediccionPartido.objects.create(
        partido=partido,
        prob_victoria_local=0.6,
        prob_empate=0.2,
        prob_victoria_visit=0.2,
        goles_local_pred=2,
        goles_visit_pred=1,
        confianza=0.6,
    )
    respuesta = client.get(
        reverse("ml-tablero"),
        {"campeonato": partido.campeonato_id},
    )

    assert respuesta.status_code == 200
    assert not Bitacora.objects.filter(accion=Bitacora.Accion.ML_PRED).exists()


def test_get_prediccion_de_asistencia_no_escribe_en_bitacora(client, admin, partido):
    client.force_authenticate(user=admin)
    respuesta = client.get(
        reverse("ml-asistencia", kwargs={"partido_id": partido.pk})
    )

    assert respuesta.status_code == 200
    assert not Bitacora.objects.filter(accion=Bitacora.Accion.ML_PRED).exists()


def test_get_riesgo_climatico_no_escribe_en_bitacora(
    client, admin, partido, monkeypatch
):
    client.force_authenticate(user=admin)
    riesgo = RiesgoClimatico.objects.create(
        partido=partido,
        nivel_riesgo=RiesgoClimatico.NivelRiesgo.BAJO,
    )
    monkeypatch.setattr(
        "apps.ml.views.ServicioClima",
        lambda: SimpleNamespace(
            consultar=lambda partido, *, persistir: riesgo
        ),
    )

    respuesta = client.get(
        reverse("ml-riesgo", kwargs={"partido_id": partido.pk})
    )

    assert respuesta.status_code == 200
    assert not Bitacora.objects.filter(accion=Bitacora.Accion.ML_PRED).exists()


def test_entrenamiento_modelo_audita_evento(client, admin, monkeypatch):
    client.force_authenticate(user=admin)
    monkeypatch.setattr("apps.ml.views.predictor_entrenar", lambda: {
        "entrenado": True, "version": "rf-prueba", "partidos": 80, "activo": False})

    respuesta = client.post(reverse("ml-entrenar"), {}, format="json")

    assert respuesta.status_code == 200
    registro = Bitacora.objects.get(accion=Bitacora.Accion.ML_PRED)
    assert registro.usuario == admin and registro.modulo == "ml"
    assert registro.resultado == Bitacora.Resultado.OK
    assert registro.detalle == {"version": "rf-prueba", "partidos": 80, "activo": False}


def test_entrenamiento_fallido_se_registra_como_error(client, admin, monkeypatch):
    client.force_authenticate(user=admin)
    monkeypatch.setattr("apps.ml.views.predictor_entrenar", lambda: {
        "entrenado": False, "motivo": "Datos insuficientes: hay 3 partidos finalizados.", "partidos": 3})

    respuesta = client.post(reverse("ml-entrenar"), {}, format="json")

    assert respuesta.status_code == 400
    registro = Bitacora.objects.get(accion=Bitacora.Accion.ML_PRED)
    assert registro.resultado == Bitacora.Resultado.ERROR and registro.detalle["partidos"] == 3
