"""F7-05/F7-06 — Planilla sin conexión: claves de idempotencia, conflicto al sincronizar y paquete de datos."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta

import pytest
from django.db import connection
from django.utils import timezone

from apps.deportes.models import Campeonato
from apps.fixture.models import Incidencia, OperacionIdempotente, Partido, Resultado
from apps.fixture.tasks import purgar_operaciones_idempotentes
from apps.fixture.tests.helpers import cliente_de, crear_escenario, crear_jugador, crear_usuario
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db
KEY = "Idempotency-Key"


@pytest.fixture
def mundo():
    esc = crear_escenario(equipos=2, canchas=1, estado=Campeonato.Estado.EN_CURSO)
    esc.local, esc.visitante = esc.equipos
    esc.j_local = [crear_jugador(esc.local, n) for n in (1, 2, 3)]
    esc.j_visit = [crear_jugador(esc.visitante, n) for n in (1, 2)]
    ahora = timezone.localtime()
    esc.partido = Partido.objects.create(
        campeonato=esc.campeonato, equipo_local=esc.local, equipo_visitante=esc.visitante, cancha=esc.canchas[0],
        fecha_hora=timezone.make_aware(datetime.combine(ahora.date(), time(10, 0))), jornada=1, duracion_min=90)
    esc.url_inc = f"/api/v1/fixture/partidos/{esc.partido.pk}/incidencia/"
    esc.url_res = f"/api/v1/fixture/partidos/{esc.partido.pk}/resultado/"
    return esc


def gol(mundo, jugador=None, minuto=10):
    return {"tipo": "GOL", "jugador": (jugador or mundo.j_local[0]).pk, "minuto": minuto}


def test_reenviar_la_misma_clave_no_duplica_la_incidencia(mundo):
    c = mundo.client_org
    primera = c.post(mundo.url_inc, gol(mundo), format="json", HTTP_IDEMPOTENCY_KEY="clave-gol-0001")
    segunda = c.post(mundo.url_inc, gol(mundo), format="json", HTTP_IDEMPOTENCY_KEY="clave-gol-0001")

    assert primera.status_code == segunda.status_code == 201
    assert segunda.data == primera.data and segunda["Idempotent-Replayed"] == "true" and "Idempotent-Replayed" not in primera
    assert Incidencia.objects.filter(partido=mundo.partido).count() == 1
    assert OperacionIdempotente.objects.count() == 1


def test_sin_cabecera_cada_envio_es_una_incidencia_distinta(mundo):
    for _ in range(2):
        mundo.client_org.post(mundo.url_inc, gol(mundo), format="json")
    assert Incidencia.objects.count() == 2 and OperacionIdempotente.objects.count() == 0


def test_cinco_incidencias_sin_red_se_sincronizan_sin_duplicados_aunque_se_reenvien(mundo):
    """Criterio de aceptación F7-06: 5 incidencias registradas sin red y sincronizadas dos veces."""
    cola = [(f"incidencia-{i:04d}", {"tipo": "TARJETA_AMARILLA", "jugador": mundo.j_local[i % 3].pk, "minuto": 10 + i}) for i in range(5)]
    for _ in range(2):                                  # el celular no supo si llegó y reintentó todo
        for clave, cuerpo in cola:
            assert mundo.client_org.post(mundo.url_inc, cuerpo, format="json", HTTP_IDEMPOTENCY_KEY=clave).status_code == 201
    assert Incidencia.objects.filter(partido=mundo.partido).count() == 5


def test_misma_clave_con_otro_contenido_se_rechaza(mundo):
    c = mundo.client_org
    c.post(mundo.url_inc, gol(mundo), format="json", HTTP_IDEMPOTENCY_KEY="clave-gol-0001")
    r = c.post(mundo.url_inc, gol(mundo, mundo.j_local[1], 20), format="json", HTTP_IDEMPOTENCY_KEY="clave-gol-0001")

    assert r.status_code == 422 and "otros datos" in r.data["detail"]
    assert Incidencia.objects.count() == 1


def test_la_clave_es_por_persona(mundo):
    mundo.client_org.post(mundo.url_inc, gol(mundo), format="json", HTTP_IDEMPOTENCY_KEY="clave-comun-01")
    r = mundo.client.post(mundo.url_inc, gol(mundo), format="json", HTTP_IDEMPOTENCY_KEY="clave-comun-01")   # otro usuario (admin)
    assert r.status_code == 201 and "Idempotent-Replayed" not in r and Incidencia.objects.count() == 2


@pytest.mark.parametrize("clave", ["corta", "con espacios no vale", "x" * 65, "raro/%&#$*"])
def test_clave_con_formato_invalido(mundo, clave):
    r = mundo.client_org.post(mundo.url_inc, gol(mundo), format="json", HTTP_IDEMPOTENCY_KEY=clave)
    assert r.status_code == 400 and Incidencia.objects.count() == 0


def test_una_operacion_fallida_no_consume_la_clave(mundo):
    c = mundo.client_org
    malo = c.post(mundo.url_inc, {"tipo": "GOL", "minuto": 5}, format="json", HTTP_IDEMPOTENCY_KEY="clave-reint-001")   # GOL sin jugador
    bueno = c.post(mundo.url_inc, gol(mundo), format="json", HTTP_IDEMPOTENCY_KEY="clave-reint-001")

    assert malo.status_code == 400 and bueno.status_code == 201 and Incidencia.objects.count() == 1


def test_resultado_reenviado_no_se_registra_dos_veces(mundo):
    c = mundo.client_org
    c.post(mundo.url_inc, gol(mundo), format="json", HTTP_IDEMPOTENCY_KEY="clave-gol-0001")
    cuerpo = {"goles_local": 1, "goles_visitante": 0}
    a = c.post(mundo.url_res, cuerpo, format="json", HTTP_IDEMPOTENCY_KEY="clave-final-001")
    b = c.post(mundo.url_res, cuerpo, format="json", HTTP_IDEMPOTENCY_KEY="clave-final-001")

    assert a.status_code == b.status_code == 201 and b.data == a.data and b["Idempotent-Replayed"] == "true"
    assert Resultado.objects.filter(partido=mundo.partido).count() == 1


def test_si_otra_persona_ya_cerro_el_partido_la_planilla_recibe_un_conflicto_409(mundo):
    mundo.client.post(mundo.url_res, {"goles_local": 0, "goles_visitante": 0}, format="json")            # el administrador lo cerró
    r = mundo.client_org.post(mundo.url_res, {"goles_local": 2, "goles_visitante": 1}, format="json", HTTP_IDEMPOTENCY_KEY="clave-final-002")

    assert r.status_code == 409 and "ya tiene resultado" in r.data["detail"]
    assert Resultado.objects.get(partido=mundo.partido).goles_local == 0            # no se sobrescribió
    assert not OperacionIdempotente.objects.filter(clave="clave-final-002").exists()


def test_se_exige_sesion_y_rol_igual_que_sin_clave(mundo):
    sin = mundo.client.__class__()
    assert sin.post(mundo.url_inc, gol(mundo), format="json", HTTP_IDEMPOTENCY_KEY="clave-gol-0001").status_code == 401
    delegado = cliente_de(mundo.local.delegado)
    assert delegado.post(mundo.url_inc, gol(mundo), format="json", HTTP_IDEMPOTENCY_KEY="clave-gol-0001").status_code == 403
    assert OperacionIdempotente.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_dos_envios_simultaneos_con_la_misma_clave_crean_una_sola_incidencia(mundo):
    def enviar(_):
        try:
            return cliente_de(mundo.organizador).post(mundo.url_inc, gol(mundo), format="json", HTTP_IDEMPOTENCY_KEY="clave-carrera-1").status_code
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        codigos = list(pool.map(enviar, range(4)))

    assert set(codigos) == {201} and Incidencia.objects.filter(partido=mundo.partido).count() == 1


def test_la_purga_borra_solo_las_claves_antiguas(mundo):
    mundo.client_org.post(mundo.url_inc, gol(mundo), format="json", HTTP_IDEMPOTENCY_KEY="clave-nueva-01")
    vieja = OperacionIdempotente.objects.create(usuario=mundo.organizador, clave="clave-vieja-01", metodo="POST", ruta="/x", huella="0" * 64)
    OperacionIdempotente.objects.filter(pk=vieja.pk).update(creado_en=timezone.now() - timedelta(days=8))

    assert purgar_operaciones_idempotentes() == 1
    assert list(OperacionIdempotente.objects.values_list("clave", flat=True)) == ["clave-nueva-01"]


# ── Paquete para trabajar sin conexión ────────────────────────────────────────

URL_PAQUETE = "/api/v1/fixture/planilla/paquete/"


def test_el_paquete_trae_partidos_de_hoy_con_plantillas_e_incidencias(mundo):
    mundo.client_org.post(mundo.url_inc, gol(mundo), format="json")

    r = mundo.client_org.get(URL_PAQUETE)

    assert r.status_code == 200 and r.data["usuario"] == mundo.organizador.pk and len(r.data["partidos"]) == 1
    p = r.data["partidos"][0]
    assert p["id"] == mundo.partido.pk and p["campeonato"]["nombre"] == mundo.campeonato.nombre and p["resultado"] is None
    assert [j["numero"] for j in p["local"]["jugadores"]] == [1, 2, 3] and len(p["visitante"]["jugadores"]) == 2
    assert p["incidencias"][0]["tipo"] == "GOL" and p["incidencias"][0]["jugador"] == mundo.j_local[0].pk


def test_el_paquete_marca_a_los_jugadores_sancionados(mundo):
    sancionado = mundo.j_local[1]
    sancionado.partidos_sancion_restantes = 2
    sancionado.save(update_fields=["partidos_sancion_restantes"])

    p = mundo.client_org.get(URL_PAQUETE).data["partidos"][0]

    marcas = {j["id"]: j["sancionado"] for j in p["local"]["jugadores"]}
    assert marcas[sancionado.pk] is True and marcas[mundo.j_local[0].pk] is False


def test_el_paquete_excluye_otros_dias_campeonatos_inactivos_y_partidos_sin_equipos(mundo):
    Partido.objects.create(campeonato=mundo.campeonato, equipo_local=mundo.local, equipo_visitante=mundo.visitante, cancha=mundo.canchas[0],
                           fecha_hora=mundo.partido.fecha_hora + timedelta(days=10), jornada=2, duracion_min=90)
    Partido.objects.create(campeonato=mundo.campeonato, equipo_local=None, equipo_visitante=None, cancha=mundo.canchas[0],
                           fecha_hora=mundo.partido.fecha_hora + timedelta(hours=3), jornada=3, duracion_min=90)
    otro = crear_escenario(equipos=2, canchas=1, estado=Campeonato.Estado.INSCRIPCION_CERRADA)
    Partido.objects.create(campeonato=otro.campeonato, equipo_local=otro.equipos[0], equipo_visitante=otro.equipos[1], cancha=otro.canchas[0],
                           fecha_hora=mundo.partido.fecha_hora, jornada=1, duracion_min=90)

    ids = [p["id"] for p in mundo.client_org.get(URL_PAQUETE).data["partidos"]]

    assert ids == [mundo.partido.pk]


def test_permisos_del_paquete(mundo):
    assert mundo.client.__class__().get(URL_PAQUETE).status_code == 401
    assert cliente_de(mundo.local.delegado).get(URL_PAQUETE).status_code == 403
    assert cliente_de(crear_usuario(Usuario.Rol.JUGADOR)).get(URL_PAQUETE).status_code == 403
    assert mundo.client.get(URL_PAQUETE).status_code == 200
    assert mundo.client_org.get(URL_PAQUETE + "?dias=abc").status_code == 200
