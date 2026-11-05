"""F6-03 / F6-07 — Pronóstico programado y reentrenamiento idempotente."""
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from apps.deportes.models import Campeonato
from apps.fixture.models import Partido
from apps.fixture.services.fixture_generator import FixtureGenerator
from apps.fixture.tasks import reconstruir_historial
from apps.fixture.tests.helpers import crear_escenario
from apps.ml import tasks
from apps.ml.models import ModeloML, RiesgoClimatico
from apps.ml.services import clima, predictor

pytestmark = pytest.mark.django_db


def _partido_en_curso(horas=30):
    esc = crear_escenario(equipos=2, canchas=1)
    (partido,) = FixtureGenerator(esc.campeonato.pk).generar()
    Campeonato.objects.filter(pk=esc.campeonato.pk).update(estado=Campeonato.Estado.EN_CURSO)
    partido.fecha_hora = timezone.now() + timedelta(hours=horas)
    partido.save()
    return esc, partido


def _servicio_con(monkeypatch, nivel):
    def consultar(self, partido, *, persistir=True):
        return clima.ServicioClima._guardar(partido, {
            "nivel_riesgo": nivel, "recomendacion": "Considerar reprogramación.", "descripcion": "x",
            "fuente_api": "Open-Meteo"}, persistir=persistir)

    monkeypatch.setattr(clima.ServicioClima, "consultar", consultar)


def test_la_tarea_de_clima_guarda_el_pronostico_y_avisa_solo_cuando_empeora(monkeypatch):
    _, partido = _partido_en_curso()
    _servicio_con(monkeypatch, RiesgoClimatico.NivelRiesgo.ALTO)

    primera = tasks.actualizar_riesgo_climatico()
    segunda = tasks.actualizar_riesgo_climatico()

    assert primera == {"actualizados": 1, "avisos": 1}
    assert segunda == {"actualizados": 1, "avisos": 0}                 # mismo nivel: no se repite el aviso
    assert RiesgoClimatico.objects.filter(partido=partido).count() == 1
    assert len(mail.outbox) == 1 and "Posible cambio por clima" in mail.outbox[0].subject


def test_un_riesgo_bajo_se_guarda_pero_no_avisa(monkeypatch):
    _partido_en_curso()
    _servicio_con(monkeypatch, RiesgoClimatico.NivelRiesgo.BAJO)

    assert tasks.actualizar_riesgo_climatico() == {"actualizados": 1, "avisos": 0}
    assert not mail.outbox


def test_sin_pronostico_no_se_guarda_nada_ni_se_avisa(monkeypatch):
    _partido_en_curso()
    _servicio_con(monkeypatch, RiesgoClimatico.NivelRiesgo.SIN_DATOS)

    assert tasks.actualizar_riesgo_climatico() == {"actualizados": 0, "avisos": 0}


def test_solo_se_pronostica_lo_cercano_y_publicado(monkeypatch):
    _partido_en_curso(horas=200)                       # fuera de las 72 h
    esc, _ = _partido_en_curso(horas=10)
    Campeonato.objects.filter(pk=esc.campeonato.pk).update(estado=Campeonato.Estado.INSCRIPCION_CERRADA)  # borrador
    _servicio_con(monkeypatch, RiesgoClimatico.NivelRiesgo.ALTO)

    assert tasks.actualizar_riesgo_climatico() == {"actualizados": 0, "avisos": 0}


def test_el_reentrenamiento_es_idempotente_y_registra_en_bitacora(tmp_path, monkeypatch):
    from apps.auditoria.models import Bitacora

    monkeypatch.setattr(predictor, "MODEL_DIR", tmp_path)
    primero = tasks.reentrenar_modelos()
    assert primero["predictor"]["entrenado"] is False and primero["asignacion"]["reentrenado"] is False
    assert Bitacora.objects.filter(modulo="ml", usuario__isnull=True).count() == 1

    monkeypatch.setattr(predictor, "construir_dataset", lambda: (None, None, None, "huella-1"))
    ModeloML.objects.create(nombre=predictor.NOMBRE_MODELO, version="rf-prueba", hash_datos="huella-1")
    segundo = tasks.reentrenar_modelos()

    assert segundo["predictor"] == {"entrenado": False, "motivo": "sin datos nuevos"}


def test_el_reentrenamiento_incorpora_partidos_reales_nuevos_al_puntuador():
    esc = crear_escenario(equipos=4, canchas=2)
    partidos = FixtureGenerator(esc.campeonato.pk).generar()
    Partido.objects.filter(pk__in=[p.pk for p in partidos[:3]]).update(estado=Partido.Estado.SUSPENDIDO)
    Partido.objects.filter(pk__in=[p.pk for p in partidos[3:]]).update(estado=Partido.Estado.FINALIZADO)

    # El puntuador necesita historial real suficiente para reentrenar; con pocos se apoya en las reglas.
    r = tasks.reentrenar_modelos()

    assert r["asignacion"]["reentrenado"] is True and r["asignacion"]["muestras_nuevas"] == 6
    assert tasks.reentrenar_modelos()["asignacion"]["reentrenado"] is False   # ya no hay nuevas


def test_reconstruir_historial_es_idempotente():
    esc = crear_escenario(equipos=3, canchas=2)
    FixtureGenerator(esc.campeonato.pk).generar()
    Campeonato.objects.filter(pk=esc.campeonato.pk).update(estado=Campeonato.Estado.EN_CURSO)

    assert reconstruir_historial() == {"campeonatos": 1}
    assert reconstruir_historial() == {"campeonatos": 1}
