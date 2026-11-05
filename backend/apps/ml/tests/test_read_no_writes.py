from datetime import date, timedelta

import pytest
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient

from apps.auditoria.models import Bitacora
from apps.deportes.models import Campeonato, Categoria, Deporte, Equipo, Facultad
from apps.fixture.models import Partido
from apps.ml.models import PrediccionAsistencia, PrediccionPartido, RiesgoClimatico
from apps.users.models import Usuario


pytestmark = pytest.mark.django_db


@pytest.fixture
def partido_ml():
    deporte = Deporte.objects.create(nombre="Deporte GET ML")
    categoria = Categoria.objects.create(deporte=deporte, nombre="Categoria GET ML")
    campeonato = Campeonato.objects.create(
        nombre="Campeonato GET ML",
        categoria=categoria,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
    )
    facultad_a = Facultad.objects.create(nombre="Facultad GET ML A", sigla="GMLA")
    facultad_b = Facultad.objects.create(nombre="Facultad GET ML B", sigla="GMLB")
    equipo_local = Equipo.objects.create(
        nombre="Local GET ML",
        facultad=facultad_a,
    )
    equipo_visitante = Equipo.objects.create(
        nombre="Visitante GET ML",
        facultad=facultad_b,
    )
    partido = Partido.objects.create(
        campeonato=campeonato,
        equipo_local=equipo_local,
        equipo_visitante=equipo_visitante,
        fecha_hora="2026-06-01T10:00:00Z",
    )
    return campeonato, partido


def test_get_de_predicciones_no_persiste_resultado_asistencia_ni_riesgo(partido_ml):
    campeonato, partido = partido_ml
    client = APIClient()
    usuario = Usuario.objects.create_user(
        email="delegado-ml-lectura@example.com",
        password="PruebaSegura123!",
        nombre="Diego",
        apellido="Delegado",
        rol=Usuario.Rol.DELEGADO,
    )
    client.force_authenticate(usuario)

    rutas = [
        reverse("ml-prediccion", kwargs={"partido_id": partido.pk}),
        reverse("ml-asistencia", kwargs={"partido_id": partido.pk}),
        reverse("ml-riesgo", kwargs={"partido_id": partido.pk}),
        reverse("ml-tablero"),
    ]
    for ruta in rutas:
        params = {"campeonato": campeonato.pk} if ruta == rutas[-1] else None
        respuesta = client.get(ruta, params or {})
        assert respuesta.status_code == 200

    assert PrediccionPartido.objects.count() == 0
    assert PrediccionAsistencia.objects.count() == 0
    assert RiesgoClimatico.objects.count() == 0
    assert Bitacora.objects.count() == 0


def test_generacion_persistente_de_prediccion_exige_operador(partido_ml):
    _, partido = partido_ml
    client = APIClient()
    ruta = reverse("ml-prediccion", kwargs={"partido_id": partido.pk})

    assert client.post(ruta, {}, format="json").status_code == 401
    organizador = Usuario.objects.create_user(
        email="organizador-ml-post@example.com",
        password="PruebaSegura123!",
        nombre="Olga",
        apellido="Organizadora",
        rol=Usuario.Rol.ORGANIZADOR,
    )
    client.force_authenticate(organizador)

    respuesta = client.post(ruta, {}, format="json")

    assert respuesta.status_code == 200
    assert PrediccionPartido.objects.filter(partido=partido).exists()
    assert Bitacora.objects.filter(
        accion=Bitacora.Accion.ML_PRED,
        objeto_id=partido.pk,
    ).exists()


def test_riesgo_climatico_get_lee_lo_guardado_y_el_post_consulta_open_meteo(partido_ml, monkeypatch):
    from apps.ml.services import clima

    _, partido = partido_ml
    partido.fecha_hora = timezone.now() + timedelta(days=2)
    partido.save()
    org = APIClient()
    org.force_authenticate(Usuario.objects.create_user(
        email="org-clima@example.com", password="PruebaSegura123!", nombre="Olga", apellido="Org",
        rol=Usuario.Rol.ORGANIZADOR))
    url = reverse("ml-riesgo", kwargs={"partido_id": partido.pk})

    # GET sin pronóstico guardado: SIN_DATOS (no "riesgo bajo") y sin llamar a la red.
    llamadas = []
    monkeypatch.setattr(clima.requests, "get", lambda *a, **k: llamadas.append(1))
    vacio = org.get(url)
    assert vacio.data["nivel_riesgo"] == "SIN_DATOS" and vacio.data["calculado"] is False and not llamadas

    class Respuesta:
        def raise_for_status(self): pass
        def json(self):
            base = timezone.localtime(timezone.now()).replace(minute=0, second=0, microsecond=0)
            horas = [(base + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(0, 24 * 5)]
            n = len(horas)
            return {"hourly": {"time": horas, "temperature_2m": [20.0] * n, "precipitation": [6.0] * n,
                               "precipitation_probability": [90] * n, "wind_speed_10m": [10.0] * n}}

    monkeypatch.setattr(clima.requests, "get", lambda *a, **k: Respuesta())
    r = org.post(url)
    assert r.status_code == 200 and r.data["calculado"] is True
    assert r.data["nivel_riesgo"] in ("ALTO", "CRITICO") and r.data["fuente_api"] == "Open-Meteo"
    assert RiesgoClimatico.objects.filter(partido=partido).count() == 1
    assert org.get(url).data["nivel_riesgo"] == r.data["nivel_riesgo"]


def test_riesgo_climatico_sin_conexion_no_pisa_el_ultimo_pronostico(partido_ml, monkeypatch):
    from apps.ml.services import clima

    _, partido = partido_ml
    partido.fecha_hora = timezone.now() + timedelta(days=1)
    partido.save()
    RiesgoClimatico.objects.create(partido=partido, nivel_riesgo="MEDIO", descripcion="previo", fuente_api="Open-Meteo")
    org = APIClient()
    org.force_authenticate(Usuario.objects.create_user(
        email="org-clima2@example.com", password="PruebaSegura123!", nombre="Olga", apellido="Org",
        rol=Usuario.Rol.ORGANIZADOR))

    def sin_red(*a, **k):
        raise clima.requests.ConnectionError("sin red")

    monkeypatch.setattr(clima.requests, "get", sin_red)
    r = org.post(reverse("ml-riesgo", kwargs={"partido_id": partido.pk}))

    assert r.data["nivel_riesgo"] == "SIN_DATOS" and r.data["calculado"] is False
    assert RiesgoClimatico.objects.get(partido=partido).nivel_riesgo == "MEDIO"   # el previo se conserva


def test_calculo_de_riesgo_considera_techo_viento_y_temperatura():
    from apps.ml.services.clima import ServicioClima

    s = ServicioClima()
    assert s.calcular_riesgo(22, 10, 20, techada=True)[0] == "BAJO"           # techada: la lluvia no cuenta
    assert s.calcular_riesgo(22, 10, 20, techada=False)[0] == "CRITICO"
    assert s.calcular_riesgo(22, 55, 0, techada=True)[0] == "ALTO"           # el viento sí afecta bajo techo
    assert s.calcular_riesgo(41, 5, 0, techada=False)[0] == "CRITICO"         # calor extremo
    assert s.calcular_riesgo(3, 5, 0, techada=False)[0] == "ALTO"
    assert s.calcular_riesgo(22, 5, 0, techada=False)[1] == "Condiciones favorables para el partido."


def test_asistencia_es_una_estimacion_declarada_y_cambia_con_la_fase(partido_ml):
    from apps.ml.services.asistencia import estimar_asistencia

    _, partido = partido_ml
    normal = estimar_asistencia(partido)
    Partido.objects.filter(pk=partido.pk).update(fase="Final")
    partido.refresh_from_db()
    final = estimar_asistencia(partido)

    assert "no se registra la asistencia real" in normal["factores"]["metodo"]
    assert final["asistencia_predicha"] > normal["asistencia_predicha"]
    assert normal["rango_min"] <= normal["asistencia_predicha"] <= normal["rango_max"]


def test_acciones_sugeridas_salen_de_datos_reales():
    from apps.fixture.tests.helpers import crear_escenario
    from apps.ml.services.recomendaciones import acciones_sugeridas

    assert acciones_sugeridas() == []      # sin datos no se inventa nada
    esc = crear_escenario(equipos=3, canchas=2)    # inscripciones cerradas, sin fixture
    acciones = acciones_sugeridas()
    assert any("aún no tiene fixture" in a["mensaje"] for a in acciones)
    assert all(a["enlace"].startswith("/gestion") for a in acciones)
    assert esc.client_org.get(reverse("ml-recomendaciones")).data["fuente"] == "datos del sistema"
