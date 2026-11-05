"""F3-01 — Creación y estados de campeonato (RF9, RF10)."""


import pytest
from rest_framework.test import APIClient
from django.urls import reverse

from apps.auditoria.models import Bitacora
from apps.deportes.models import Campeonato, Categoria, Deporte
from apps.deportes.services import transiciones_permitidas
from apps.fixture.models import Partido
from apps.fixture.services.fixture_generator import FixtureError, FixtureGenerator
from apps.fixture.tests.helpers import (
    crear_escenario, crear_usuario, cliente_de,
)
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db
E = Campeonato.Estado


def cambiar(client, campeonato, estado):
    return client.patch(
        reverse("campeonato-cambiar-estado", kwargs={"pk": campeonato.pk}),
        {"estado": estado},
        format="json",
    )


@pytest.mark.parametrize(
    ("origen", "destino"),
    [
        (E.PLANIFICACION, E.INSCRIPCIONES),
        (E.PLANIFICACION, E.CANCELADO),
        (E.INSCRIPCIONES, E.PLANIFICACION),
        (E.INSCRIPCIONES, E.CANCELADO),
        (E.INSCRIPCIONES, E.INSCRIPCION_CERRADA),
        (E.INSCRIPCION_CERRADA, E.INSCRIPCIONES),
        (E.INSCRIPCION_CERRADA, E.CANCELADO),
        (E.EN_CURSO, E.CANCELADO),
    ],
)
def test_transiciones_validas(origen, destino):
    esc = crear_escenario(equipos=2, canchas=1, estado=origen)

    respuesta = cambiar(esc.client, esc.campeonato, destino)

    assert respuesta.status_code == 200
    esc.campeonato.refresh_from_db()
    assert esc.campeonato.estado == destino
    assert respuesta.data["transiciones_permitidas"] == transiciones_permitidas(destino)


@pytest.mark.parametrize(
    ("origen", "destino"),
    [
        (E.PLANIFICACION, E.EN_CURSO),
        (E.PLANIFICACION, E.FINALIZADO),
        (E.PLANIFICACION, E.INSCRIPCION_CERRADA),
        (E.INSCRIPCIONES, E.EN_CURSO),
        (E.INSCRIPCIONES, E.FINALIZADO),
        (E.EN_CURSO, E.INSCRIPCION_CERRADA),
        (E.EN_CURSO, E.INSCRIPCIONES),
        (E.EN_CURSO, E.PLANIFICACION),
        (E.FINALIZADO, E.CANCELADO),
        (E.FINALIZADO, E.EN_CURSO),
        (E.CANCELADO, E.INSCRIPCIONES),
        (E.CANCELADO, E.PLANIFICACION),
        (E.PLANIFICACION, E.PLANIFICACION),
    ],
)
def test_transiciones_invalidas_devuelven_400_y_se_registran(origen, destino):
    esc = crear_escenario(equipos=2, canchas=1, estado=origen)

    respuesta = cambiar(esc.client, esc.campeonato, destino)

    assert respuesta.status_code == 400
    assert "estado" in respuesta.data
    esc.campeonato.refresh_from_db()
    assert esc.campeonato.estado == origen
    registro = Bitacora.objects.get(accion=Bitacora.Accion.CAMBIO_ESTADO)
    assert registro.resultado == Bitacora.Resultado.ERROR
    assert registro.detalle["anterior"] == origen
    assert registro.detalle["motivos"]


def test_estado_inexistente_es_400():
    esc = crear_escenario(equipos=2, canchas=1)

    respuesta = cambiar(esc.client, esc.campeonato, "VOLANDO")

    assert respuesta.status_code == 400
    assert "Estado inválido" in str(respuesta.data)


def test_iniciar_exige_equipos_aprobados_y_fixture():
    esc = crear_escenario(equipos=2, canchas=1)

    sin_fixture = cambiar(esc.client, esc.campeonato, E.EN_CURSO)
    assert sin_fixture.status_code == 400
    assert "fixture" in str(sin_fixture.data).lower()

    FixtureGenerator(esc.campeonato.pk).generar()
    con_fixture = cambiar(esc.client, esc.campeonato, E.EN_CURSO)
    assert con_fixture.status_code == 200

    solo_uno = crear_escenario(equipos=1, canchas=1)
    respuesta = cambiar(solo_uno.client, solo_uno.campeonato, E.EN_CURSO)
    assert respuesta.status_code == 400
    assert "al menos 2 equipos" in str(respuesta.data)


def test_finalizar_exige_que_no_queden_partidos_pendientes():
    esc = crear_escenario(equipos=2, canchas=1)
    (partido,) = FixtureGenerator(esc.campeonato.pk).generar()
    Campeonato.objects.filter(pk=esc.campeonato.pk).update(estado=E.EN_CURSO)

    pendiente = cambiar(esc.client, esc.campeonato, E.FINALIZADO)
    assert pendiente.status_code == 400
    assert "sin resultado" in str(pendiente.data)

    Partido.objects.filter(pk=partido.pk).update(estado=Partido.Estado.FINALIZADO)
    assert cambiar(esc.client, esc.campeonato, E.FINALIZADO).status_code == 200


def test_cambio_valido_se_registra_en_bitacora():
    esc = crear_escenario(equipos=2, canchas=1, estado=E.PLANIFICACION)

    cambiar(esc.client, esc.campeonato, E.INSCRIPCIONES)

    registro = Bitacora.objects.get(accion=Bitacora.Accion.CAMBIO_ESTADO)
    assert registro.resultado == Bitacora.Resultado.OK
    assert registro.detalle == {"anterior": E.PLANIFICACION, "nuevo": E.INSCRIPCIONES}


def test_el_organizador_puede_cambiar_el_estado_pero_el_delegado_no():
    esc = crear_escenario(equipos=2, canchas=1, estado=E.PLANIFICACION)
    delegado = crear_usuario(Usuario.Rol.DELEGADO, esc.equipos[0].facultad)

    assert cambiar(esc.client_org, esc.campeonato, E.INSCRIPCIONES).status_code == 200
    assert cambiar(cliente_de(delegado), esc.campeonato, E.CANCELADO).status_code == 403


def test_el_estado_no_se_edita_por_los_endpoints_de_escritura():
    esc = crear_escenario(equipos=2, canchas=1, estado=E.PLANIFICACION)

    esc.client.patch(
        reverse("campeonato-detail", kwargs={"pk": esc.campeonato.pk}),
        {"estado": E.FINALIZADO, "nombre": "Renombrado"},
        format="json",
    )

    esc.campeonato.refresh_from_db()
    assert esc.campeonato.nombre == "Renombrado"
    assert esc.campeonato.estado == E.PLANIFICACION


# ── Validaciones de creación ─────────────────────────────────────────────────

@pytest.fixture
def datos_campeonato():
    deporte = Deporte.objects.create(nombre="Deporte alta")
    categoria = Categoria.objects.create(deporte=deporte, nombre="Categoría alta")
    return {
        "nombre": "Copa nueva",
        "categoria": categoria.pk,
        "formato": "LIGA",
        "fecha_inicio": "2027-05-01",
        "fecha_fin": "2027-06-30",
        "max_equipos": 8,
    }


def crear(client, datos):
    return client.post(reverse("campeonato-list"), datos, format="json")


def test_alta_valida_nace_en_planificacion_aunque_se_envie_otro_estado(datos_campeonato):
    esc = crear_escenario(equipos=0, canchas=0)

    respuesta = crear(esc.client, {**datos_campeonato, "estado": "EN_CURSO"})

    assert respuesta.status_code == 201
    assert respuesta.data["estado"] == E.PLANIFICACION
    assert respuesta.data["transiciones_permitidas"] == [E.INSCRIPCIONES, E.CANCELADO]


@pytest.mark.parametrize(
    ("cambio", "campo"),
    [
        ({"fecha_fin": "2027-04-01"}, "fecha_fin"),
        ({"max_equipos": 1}, "max_equipos"),
        ({"fecha_cierre_inscripcion": "2027-05-01T10:00:00Z"}, "fecha_cierre_inscripcion"),
        ({"fecha_cierre_inscripcion": "2027-06-01T10:00:00Z"}, "fecha_cierre_inscripcion"),
        ({"min_jugadores": 20, "max_jugadores": 10}, "min_jugadores"),
    ],
)
def test_alta_rechaza_datos_incoherentes(datos_campeonato, cambio, campo):
    esc = crear_escenario(equipos=0, canchas=0)

    respuesta = crear(esc.client, {**datos_campeonato, **cambio})

    assert respuesta.status_code == 400
    assert campo in respuesta.data


def test_alta_acepta_cierre_de_inscripcion_anterior_al_inicio(datos_campeonato):
    esc = crear_escenario(equipos=0, canchas=0)

    respuesta = crear(esc.client, {
        **datos_campeonato, "fecha_cierre_inscripcion": "2027-04-20T10:00:00Z",
    })

    assert respuesta.status_code == 201


def test_alta_rechaza_categoria_inactiva(datos_campeonato):
    esc = crear_escenario(equipos=0, canchas=0)
    Categoria.objects.filter(pk=datos_campeonato["categoria"]).update(activa=False)

    respuesta = crear(esc.client, datos_campeonato)

    assert respuesta.status_code == 400
    assert "categoria" in respuesta.data


def test_flujo_oficial_abrir_cerrar_generar_iniciar():
    esc = crear_escenario(equipos=3, canchas=2, estado=E.INSCRIPCIONES)

    # Con las inscripciones abiertas no se puede generar el fixture (RF10/RF11).
    with pytest.raises(FixtureError, match="Cierra las inscripciones"):
        FixtureGenerator(esc.campeonato.pk).generar()
    assert cambiar(esc.client, esc.campeonato, E.EN_CURSO).status_code == 400

    assert cambiar(esc.client, esc.campeonato, E.INSCRIPCION_CERRADA).status_code == 200
    sin_fixture = cambiar(esc.client, esc.campeonato, E.EN_CURSO)
    assert sin_fixture.status_code == 400 and "fixture" in str(sin_fixture.data).lower()

    assert len(FixtureGenerator(esc.campeonato.pk).generar()) == 3
    reabrir = cambiar(esc.client, esc.campeonato, E.INSCRIPCIONES)
    assert reabrir.status_code == 400 and "ya tiene fixture" in str(reabrir.data)
    assert cambiar(esc.client, esc.campeonato, E.EN_CURSO).status_code == 200


def test_cerrar_inscripciones_exige_dos_equipos_aprobados():
    esc = crear_escenario(equipos=1, canchas=1, estado=E.INSCRIPCIONES)

    respuesta = cambiar(esc.client, esc.campeonato, E.INSCRIPCION_CERRADA)

    assert respuesta.status_code == 400 and "al menos 2 equipos" in str(respuesta.data)


def test_el_fixture_es_borrador_hasta_que_el_campeonato_inicia():
    esc = crear_escenario(equipos=2, canchas=1)
    (partido,) = FixtureGenerator(esc.campeonato.pk).generar()
    anonimo = APIClient()
    lista = reverse("partido-list")
    detalle = reverse("partido-detail", kwargs={"pk": partido.pk})

    # Gestión sí ve el borrador; el público y los delegados no.
    assert esc.client.get(lista, {"campeonato": esc.campeonato.pk}).data["count"] == 1
    assert anonimo.get(lista, {"campeonato": esc.campeonato.pk}).data["count"] == 0
    assert anonimo.get(detalle).status_code == 404
    delegado = crear_usuario(Usuario.Rol.DELEGADO, esc.equipos[0].facultad)
    assert cliente_de(delegado).get(lista).data["count"] == 0

    assert cambiar(esc.client, esc.campeonato, E.EN_CURSO).status_code == 200
    assert anonimo.get(lista, {"campeonato": esc.campeonato.pk}).data["count"] == 1
    assert anonimo.get(detalle).status_code == 200


# ── Integridad: borrar y editar un campeonato con actividad ───────────────────

def test_solo_se_elimina_un_campeonato_sin_actividad_y_queda_en_bitacora():
    libre = crear_escenario(equipos=0, canchas=0, estado=E.PLANIFICACION)
    en_curso = crear_escenario(equipos=2, canchas=1, estado=E.INSCRIPCIONES)

    bloqueado = en_curso.client.delete(reverse("campeonato-detail", kwargs={"pk": en_curso.campeonato.pk}))
    permitido = libre.client.delete(reverse("campeonato-detail", kwargs={"pk": libre.campeonato.pk}))

    assert bloqueado.status_code == 400 and "Cancélalo" in str(bloqueado.data)
    assert Campeonato.objects.filter(pk=en_curso.campeonato.pk).exists()
    assert permitido.status_code == 204 and not Campeonato.objects.filter(pk=libre.campeonato.pk).exists()
    assert Bitacora.objects.filter(accion=Bitacora.Accion.ELIMINAR, modulo="campeonato").count() == 1


def test_un_campeonato_con_resultados_no_se_elimina_ni_cancelado():
    esc = crear_escenario(equipos=2, canchas=1)
    (partido,) = FixtureGenerator(esc.campeonato.pk).generar()
    esc.client.post(reverse("partido-registrar-resultado", kwargs={"pk": partido.pk}),
                    {"goles_local": 1, "goles_visitante": 0}, format="json")
    Campeonato.objects.filter(pk=esc.campeonato.pk).update(estado=E.CANCELADO)

    respuesta = esc.client.delete(reverse("campeonato-detail", kwargs={"pk": esc.campeonato.pk}))

    assert respuesta.status_code == 400 and Campeonato.objects.filter(pk=esc.campeonato.pk).exists()


def test_con_fixture_generado_no_se_cambia_formato_ni_categoria_ni_el_cupo_bajo_los_aprobados():
    esc = crear_escenario(equipos=3, canchas=2)
    FixtureGenerator(esc.campeonato.pk).generar()
    url = reverse("campeonato-detail", kwargs={"pk": esc.campeonato.pk})

    formato = esc.client.patch(url, {"formato": "ELIMINACION"}, format="json")
    cupo = esc.client.patch(url, {"max_equipos": 2}, format="json")
    nombre = esc.client.patch(url, {"nombre": "Nuevo nombre"}, format="json")

    assert formato.status_code == 400 and "formato" in formato.data
    assert cupo.status_code == 400 and "max_equipos" in cupo.data
    assert nombre.status_code == 200
