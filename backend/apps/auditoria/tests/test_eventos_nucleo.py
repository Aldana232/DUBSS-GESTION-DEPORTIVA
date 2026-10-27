"""Pruebas de auditoría de acciones deportivas, reportes y accesos denegados."""
from datetime import date
from types import SimpleNamespace

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auditoria.models import Bitacora
from apps.deportes.models import Campeonato, Categoria, Deporte, Equipo
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
        deporte=deporte,
        categoria=categoria,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
        creado_por=admin,
    )


@pytest.fixture
def equipos(campeonato):
    return (
        Equipo.objects.create(
            campeonato=campeonato,
            nombre="Local",
            facultad="Facultad A",
        ),
        Equipo.objects.create(
            campeonato=campeonato,
            nombre="Visitante",
            facultad="Facultad B",
        ),
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
        rol=Usuario.Rol.DEPORTISTA,
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
        {"estado": Campeonato.Estado.EN_CURSO},
        format="json",
    )

    assert respuesta.status_code == 200
    registro = Bitacora.objects.get(accion=Bitacora.Accion.CAMBIO_ESTADO)
    assert registro.usuario == admin
    assert registro.entidad == "campeonato"
    assert registro.entidad_id == campeonato.pk
    assert registro.detalle == {
        "anterior": Campeonato.Estado.PLANIFICACION,
        "nuevo": Campeonato.Estado.EN_CURSO,
    }


def test_generar_fixture_audita_creados_y_eliminados(
    client, admin, campeonato, partido, monkeypatch
):
    client.force_authenticate(user=admin)
    monkeypatch.setattr(
        "apps.fixture.views.FixtureGenerator",
        lambda **kwargs: SimpleNamespace(generar=lambda usar_ml=False: [partido]),
    )

    respuesta = client.post(
        reverse("fixture-generar"),
        {"campeonato_id": campeonato.pk},
        format="json",
    )

    assert respuesta.status_code == 201
    registro = Bitacora.objects.get(accion=Bitacora.Accion.GENERAR_FIXTURE)
    assert registro.usuario == admin
    assert registro.entidad_id == campeonato.pk
    assert registro.detalle == {
        "operacion": "generar",
        "cantidad_partidos": 1,
        "partidos_eliminados": 1,
    }


def test_eliminar_partido_audita_eliminacion_del_fixture(client, admin, partido):
    client.force_authenticate(user=admin)

    respuesta = client.delete(
        reverse("partido-detail", kwargs={"pk": partido.pk})
    )

    assert respuesta.status_code == 204
    registro = Bitacora.objects.get(accion=Bitacora.Accion.GENERAR_FIXTURE)
    assert registro.usuario == admin
    assert registro.entidad_id == partido.campeonato_id
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
    assert registro.entidad == "partido"
    assert registro.entidad_id == partido.pk
    assert registro.detalle == {"goles_local": 2, "goles_visitante": 1}


def test_registrar_incidencia_audita_tipo_y_minuto(client, admin, partido):
    client.force_authenticate(user=admin)

    respuesta = client.post(
        reverse("partido-registrar-incidencia", kwargs={"pk": partido.pk}),
        {
            "partido": partido.pk,
            "tipo": Incidencia.Tipo.GOL,
            "minuto": 12,
        },
        format="json",
    )

    assert respuesta.status_code == 201
    incidencia = Incidencia.objects.get(partido=partido)
    registro = Bitacora.objects.get(accion=Bitacora.Accion.REGISTRAR_INCIDENCIA)
    assert registro.usuario == admin
    assert registro.entidad_id == partido.pk
    assert registro.detalle == {
        "tipo": Incidencia.Tipo.GOL,
        "minuto": 12,
        "incidencia_id": incidencia.pk,
    }


@pytest.mark.parametrize(
    ("nombre_url", "formato"),
    [("reporte-pdf", "PDF"), ("reporte-excel", "Excel")],
)
def test_exportacion_de_reporte_audita_formato(
    client, campeonato, nombre_url, formato
):
    respuesta = client.get(
        reverse(nombre_url, kwargs={"campeonato_id": campeonato.pk})
    )

    assert respuesta.status_code == 200
    registro = Bitacora.objects.get(accion=Bitacora.Accion.EXPORTAR)
    assert registro.entidad == "campeonato"
    assert registro.entidad_id == campeonato.pk
    assert registro.detalle == {"formato": formato}


def test_prediccion_de_partido_audita_evento(
    client, partido, monkeypatch
):
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
        lambda: SimpleNamespace(predecir=lambda partido: prediccion),
    )

    respuesta = client.get(
        reverse("ml-prediccion", kwargs={"partido_id": partido.pk})
    )

    assert respuesta.status_code == 200
    registro = Bitacora.objects.get(accion=Bitacora.Accion.ML_PRED)
    assert registro.entidad == "partido"
    assert registro.entidad_id == partido.pk
    assert registro.descripcion == "Predicción del resultado del partido generada."


def test_tablero_de_predicciones_audita_cantidad_de_partidos(
    client, partido, monkeypatch
):
    partido.estado = Partido.Estado.PROGRAMADO
    partido.save(update_fields=["estado"])
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
        lambda: SimpleNamespace(predecir=lambda partido: prediccion),
    )

    respuesta = client.get(
        reverse("ml-tablero"),
        {"campeonato": partido.campeonato_id},
    )

    assert respuesta.status_code == 200
    registro = Bitacora.objects.get(accion=Bitacora.Accion.ML_PRED)
    assert registro.entidad == "campeonato"
    assert registro.entidad_id == partido.campeonato_id
    assert registro.detalle == {"partidos": 1}


def test_prediccion_de_asistencia_audita_evento(client, partido):
    respuesta = client.get(
        reverse("ml-asistencia", kwargs={"partido_id": partido.pk})
    )

    assert respuesta.status_code == 200
    registro = Bitacora.objects.get(accion=Bitacora.Accion.ML_PRED)
    assert registro.entidad == "partido"
    assert registro.entidad_id == partido.pk
    assert registro.descripcion == "Predicción de asistencia generada."


def test_riesgo_climatico_audita_evento(client, partido, monkeypatch):
    riesgo = RiesgoClimatico.objects.create(
        partido=partido,
        nivel_riesgo=RiesgoClimatico.NivelRiesgo.BAJO,
    )
    monkeypatch.setattr(
        "apps.ml.views.ServicioClima",
        lambda: SimpleNamespace(consultar=lambda partido: riesgo),
    )

    respuesta = client.get(
        reverse("ml-riesgo", kwargs={"partido_id": partido.pk})
    )

    assert respuesta.status_code == 200
    registro = Bitacora.objects.get(accion=Bitacora.Accion.ML_PRED)
    assert registro.entidad == "partido"
    assert registro.entidad_id == partido.pk
    assert registro.descripcion == "Pronóstico de riesgo climático consultado."


def test_entrenamiento_modelo_audita_evento(client, admin, campeonato, monkeypatch):
    client.force_authenticate(user=admin)
    monkeypatch.setattr(
        "apps.ml.views.PredictorResultados",
        lambda: SimpleNamespace(entrenar=lambda campeonato_id: {
            "partidos_entrenados": 8,
            "accuracy_training": 0.9,
        }),
    )

    respuesta = client.post(
        reverse("ml-entrenar"),
        {"campeonato_id": campeonato.pk},
        format="json",
    )

    assert respuesta.status_code == 200
    registro = Bitacora.objects.get(accion=Bitacora.Accion.ML_PRED)
    assert registro.usuario == admin
    assert registro.entidad == "campeonato"
    assert registro.entidad_id == campeonato.pk
    assert registro.detalle == {"partidos_entrenados": 8}


def test_entrenamiento_fallido_se_registra_como_error(
    client, admin, campeonato, monkeypatch
):
    client.force_authenticate(user=admin)
    monkeypatch.setattr(
        "apps.ml.views.PredictorResultados",
        lambda: SimpleNamespace(
            entrenar=lambda campeonato_id: {
                "error": "Se necesitan al menos 5 partidos finalizados para entrenar."
            }
        ),
    )

    respuesta = client.post(
        reverse("ml-entrenar"),
        {"campeonato_id": campeonato.pk},
        format="json",
    )

    assert respuesta.status_code == 200
    registro = Bitacora.objects.get(accion=Bitacora.Accion.ML_PRED)
    assert registro.resultado == Bitacora.Resultado.ERROR
    assert registro.descripcion == "Entrenamiento del modelo de resultados fallido."
