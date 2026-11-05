"""F5b-03/04 — Optimizador CP-SAT + Random Forest integrado al generador (RF11)."""
import time
from datetime import datetime, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auditoria.models import Bitacora
from apps.deportes.models import Campeonato, Inscripcion, RestriccionHorarioFacultad
from apps.fixture.models import Partido
from apps.fixture.services import metricas
from apps.fixture.services.fixture_generator import FixtureError, FixtureGenerator
from apps.instalaciones.models import BloqueoCancha, HorarioCancha
from apps.ml.services import asignacion_scorer as sc
from apps.users.models import Usuario

from .helpers import cliente_de, crear_escenario, crear_usuario, hay_solapes

pytestmark = pytest.mark.django_db


def generar_ml(esc, **kwargs):
    gen = FixtureGenerator(esc.campeonato.pk, **kwargs)
    return gen, gen.generar(usar_ml=True)


@pytest.mark.parametrize("n_equipos", [4, 5, 8])
def test_ml_genera_fixture_valido_sin_conflictos_y_marca_generado_por_ml(n_equipos):
    esc = crear_escenario(equipos=n_equipos, canchas=2)

    gen, partidos = generar_ml(esc)

    assert len(partidos) == n_equipos * (n_equipos - 1) // 2
    assert all(p.generado_por_ml for p in partidos)
    assert gen.resultado["generado_por_ml"] is True and gen.resultado["aviso"] == ""
    assert hay_solapes(Partido.objects.filter(campeonato=esc.campeonato)) is None
    assert gen.resultado["calidad"]["conflictos"] == 0
    assert gen.resultado["ml"]["modelo_version"].startswith("asignacion-rf-")
    assert 0 <= gen.resultado["ml"]["puntaje_medio"] <= 1
    parejas = {frozenset((p.equipo_local_id, p.equipo_visitante_id)) for p in partidos}
    assert len(parejas) == len(partidos)


def test_veinte_equipos_con_ml_en_menos_de_10_segundos_y_cero_conflictos():
    esc = crear_escenario(equipos=20, canchas=3)
    sc.obtener_scorer()   # el modelo entrenado es una precondición, no parte del tiempo de generación

    inicio = time.perf_counter()
    gen, partidos = generar_ml(esc)
    duracion = time.perf_counter() - inicio

    assert gen.resultado["generado_por_ml"] is True, gen.resultado["aviso"]
    assert len(partidos) == 190
    assert gen.resultado["calidad"]["conflictos"] == 0
    assert hay_solapes(Partido.objects.filter(campeonato=esc.campeonato)) is None
    assert duracion < 10, f"El fixture ML de 20 equipos tardó {duracion:.1f} s (RNF04): {gen.resultado['ml']}"


def test_ml_prefiere_horarios_ideales_que_el_metodo_base():
    esc = crear_escenario(equipos=8, canchas=2)
    FixtureGenerator(esc.campeonato.pk).generar()
    base = metricas.calcular_calidad(esc.campeonato)["en_franja_ideal_pct"]

    gen, _ = generar_ml(esc)

    # El método base llena desde las 08:00; el ML reparte en la franja que el modelo califica mejor.
    assert gen.resultado["calidad"]["en_franja_ideal_pct"] > base
    assert gen.resultado["calidad"]["en_franja_ideal_pct"] >= 80


def test_ml_respeta_descanso_minimo_entre_partidos_de_un_equipo(settings):
    settings.FIXTURE_DESCANSO_MIN_HORAS = 48
    esc = crear_escenario(equipos=6, canchas=2)

    gen, _ = generar_ml(esc, dias_entre_jornadas=4)

    assert gen.resultado["generado_por_ml"] is True
    assert gen.resultado["calidad"]["descanso_minimo_dias"] >= 2


def test_ml_respeta_bloqueos_de_cancha():
    esc = crear_escenario(equipos=2, canchas=1)
    dia = timezone.make_aware(datetime.combine(esc.campeonato.fecha_inicio, datetime.min.time()))
    BloqueoCancha.objects.create(
        cancha=esc.canchas[0], fecha_inicio=dia, fecha_fin=dia + timedelta(days=3),
        tipo=BloqueoCancha.Tipo.MANTENIMIENTO, motivo="Pintura",
    )

    _, (partido,) = generar_ml(esc)

    assert partido.fecha_hora >= dia + timedelta(days=3)


def test_ml_respeta_restricciones_de_facultad():
    esc = crear_escenario(equipos=2, canchas=1)
    for dia in range(7):
        RestriccionHorarioFacultad.objects.create(
            facultad=esc.equipos[0].facultad, dia_semana=dia, hora_inicio="08:00", hora_fin="14:00", motivo="Clases",
        )

    _, (partido,) = generar_ml(esc)

    assert timezone.localtime(partido.fecha_hora).hour >= 14


def test_ml_no_programa_a_un_equipo_en_dos_campeonatos_a_la_vez():
    esc1 = crear_escenario(equipos=2, canchas=2)
    esc2 = crear_escenario(equipos=0, canchas=0, deporte=esc1.deporte)
    for e in esc1.equipos:
        Inscripcion.objects.create(campeonato=esc2.campeonato, equipo=e, estado=Inscripcion.Estado.APROBADA)

    generar_ml(esc1)
    generar_ml(esc2)

    assert hay_solapes(Partido.objects.all()) is None


def test_eliminacion_directa_con_ml_enlaza_las_rondas_y_marca_ml():
    esc = crear_escenario(equipos=6, canchas=2, formato=Campeonato.Formato.ELIMINACION)

    gen, partidos = generar_ml(esc)

    assert len(partidos) == 5 and all(p.generado_por_ml for p in partidos)
    assert gen.resultado["calidad"]["conflictos"] == 0
    final = [p for p in partidos if p.fase == "Final"][0]
    assert final.partido_origen_local_id and final.partido_origen_visitante_id


def test_si_el_solver_no_encuentra_solucion_cae_al_metodo_base_con_aviso(monkeypatch):
    from apps.fixture.services import fixture_optimizer as fo

    def sin_solucion(*a, **k):
        raise fo.OptimizadorSinSolucion("No hay cancha y horario.")

    monkeypatch.setattr(fo, "optimizar_fixture", sin_solucion)
    esc = crear_escenario(equipos=4, canchas=2)

    gen, partidos = generar_ml(esc)

    assert len(partidos) == 6 and not any(p.generado_por_ml for p in partidos)
    assert gen.resultado["generado_por_ml"] is False
    assert "Se usó el método base" in gen.resultado["aviso"]


def test_si_el_modelo_no_esta_disponible_cae_al_metodo_base_con_aviso(monkeypatch):
    from apps.fixture.services import fixture_optimizer as fo

    def sin_modelo(*a, **k):
        raise sc.ModeloNoDisponible("Datos insuficientes.")

    monkeypatch.setattr(fo, "optimizar_fixture", sin_modelo)
    esc = crear_escenario(equipos=4, canchas=2)

    gen, partidos = generar_ml(esc)

    assert len(partidos) == 6 and not gen.resultado["generado_por_ml"]
    assert "modelo de ML no está disponible" in gen.resultado["aviso"]


def test_un_error_inesperado_del_ml_tampoco_impide_generar_el_fixture(monkeypatch):
    from apps.fixture.services import fixture_optimizer as fo

    monkeypatch.setattr(fo, "optimizar_fixture", lambda *a, **k: 1 / 0)
    esc = crear_escenario(equipos=4, canchas=2)

    gen, partidos = generar_ml(esc)

    assert len(partidos) == 6 and "falló de forma inesperada" in gen.resultado["aviso"]


def test_sin_horarios_el_ml_y_el_metodo_base_fallan_con_mensaje_claro():
    esc = crear_escenario(equipos=2, canchas=1)
    HorarioCancha.objects.all().delete()
    inicio = time.perf_counter()

    with pytest.raises(FixtureError, match="No hay cancha y horario disponibles"):
        FixtureGenerator(esc.campeonato.pk).generar(usar_ml=True)

    assert time.perf_counter() - inicio < 10
    assert Partido.objects.count() == 0


def test_regenerar_con_ml_reemplaza_el_fixture_anterior_de_forma_atomica():
    esc = crear_escenario(equipos=4, canchas=2)
    FixtureGenerator(esc.campeonato.pk).generar()
    anteriores = set(Partido.objects.values_list("pk", flat=True))

    generar_ml(esc)

    nuevos = set(Partido.objects.values_list("pk", flat=True))
    assert len(nuevos) == 6 and not (anteriores & nuevos)
    assert all(Partido.objects.filter(pk__in=nuevos).values_list("generado_por_ml", flat=True))


# ── API ───────────────────────────────────────────────────────────────────────

def test_api_generar_con_ml_devuelve_calidad_modelo_y_audita():
    esc = crear_escenario(equipos=4, canchas=2)

    r = esc.client.post(reverse("fixture-generar"), {"campeonato_id": esc.campeonato.pk, "usar_ml": True}, format="json")

    assert r.status_code == 201
    assert r.data["generado_por_ml"] is True and r.data["aviso"] == ""
    assert r.data["calidad"]["conflictos"] == 0 and r.data["calidad"]["partidos"] == 6
    assert r.data["ml"]["modelo_version"]
    assert all(p["generado_por_ml"] for p in r.data["partidos"])
    registro = Bitacora.objects.get(accion=Bitacora.Accion.GENERAR_FIXTURE)
    assert registro.detalle["generado_por_ml"] is True


def test_api_generar_sin_ml_no_marca_ml():
    esc = crear_escenario(equipos=4, canchas=2)

    r = esc.client.post(reverse("fixture-generar"), {"campeonato_id": esc.campeonato.pk}, format="json")

    assert r.status_code == 201 and r.data["generado_por_ml"] is False and r.data["ml"] is None
    assert r.data["calidad"]["conflictos"] == 0


def test_api_calidad_del_fixture_y_permisos():
    esc = crear_escenario(equipos=4, canchas=2)
    generar_ml(esc)
    url = reverse("fixture-calidad")

    r = esc.client_org.get(url, {"campeonato": esc.campeonato.pk})
    assert r.status_code == 200 and r.data["generado_por_ml"] is True and r.data["conflictos"] == 0
    assert esc.client.get(url).status_code == 400
    assert esc.client.get(url, {"campeonato": 999999}).status_code == 404
    assert APIClient().get(url, {"campeonato": esc.campeonato.pk}).status_code == 401
    delegado = cliente_de(crear_usuario(Usuario.Rol.DELEGADO, esc.equipos[0].facultad))
    assert delegado.get(url, {"campeonato": esc.campeonato.pk}).status_code == 403


def test_api_estado_y_reentrenamiento_del_modelo_de_asignacion():
    esc = crear_escenario(equipos=2, canchas=1)
    url = reverse("ml-asignacion")

    info = esc.client_org.get(url)
    assert info.status_code == 200 and "entrenado" in info.data and "muestras_totales" in info.data
    assert esc.client_org.post(url).status_code == 403          # reentrenar es solo del administrador
    assert APIClient().get(url).status_code == 401
    delegado = cliente_de(crear_usuario(Usuario.Rol.DELEGADO, esc.equipos[0].facultad))
    assert delegado.get(url).status_code == 403

    r = esc.client.post(url)
    assert r.status_code == 200 and r.data["entrenado"] is True and r.data["exactitud"] > 0.9
    assert Bitacora.objects.filter(accion=Bitacora.Accion.ML_PRED, modulo="ml").exists()


# ── Métricas ──────────────────────────────────────────────────────────────────

def test_metricas_detectan_un_solape_real_de_equipo():
    esc = crear_escenario(equipos=4, canchas=3)
    FixtureGenerator(esc.campeonato.pk).generar()
    a = Partido.objects.filter(campeonato=esc.campeonato).order_by("pk").first()
    b = next(p for p in Partido.objects.filter(campeonato=esc.campeonato).exclude(pk=a.pk)
             if {p.equipo_local_id, p.equipo_visitante_id} & {a.equipo_local_id, a.equipo_visitante_id})
    assert metricas.calcular_calidad(esc.campeonato)["conflictos"] == 0
    libre = next(c for c in esc.canchas if c.pk not in (a.cancha_id,) and not Partido.objects.filter(
        cancha=c, fecha_hora=a.fecha_hora).exists())

    # Se fuerza que un equipo juegue dos partidos a la vez (en otra cancha, para no violar la restricción de cancha).
    Partido.objects.filter(pk=b.pk).update(cancha=libre, fecha_hora=a.fecha_hora, fecha_hora_fin=a.fecha_hora_fin)

    assert metricas.calcular_calidad(esc.campeonato)["conflictos"] >= 1


def test_metricas_de_un_fixture_normal():
    esc = crear_escenario(equipos=4, canchas=2)
    FixtureGenerator(esc.campeonato.pk).generar()

    calidad = metricas.calcular_calidad(esc.campeonato)

    assert calidad["partidos"] == 6 and calidad["conflictos"] == 0
    assert calidad["descanso_promedio_dias"] is not None and 0 <= calidad["equidad_pct"] <= 100


def test_metricas_sin_partidos():
    esc = crear_escenario(equipos=2, canchas=1)
    assert metricas.calcular_calidad(esc.campeonato)["partidos"] == 0
