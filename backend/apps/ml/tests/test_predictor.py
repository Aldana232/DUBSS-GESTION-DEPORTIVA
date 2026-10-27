"""Pruebas del entrenamiento del predictor de resultados."""
from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.deportes.models import Campeonato, Categoria, Deporte, Equipo
from apps.fixture.models import Partido, Resultado
from apps.ml.services import predictor
from apps.ml.services.predictor import PredictorResultados
from apps.users.models import Usuario


pytestmark = pytest.mark.django_db


def test_entrenar_con_partidos_finalizados_funciona_y_guarda_modelo(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        predictor,
        "MODEL_PATH",
        tmp_path / "resultado_predictor.joblib",
    )
    usuario = Usuario.objects.create_user(
        email="entrenador-ml@uagrm.edu.bo",
        password="Entrenamiento123!",
        nombre="Entrenador",
        apellido="ML",
    )
    deporte = Deporte.objects.create(nombre="Futbol predictor")
    categoria = Categoria.objects.create(deporte=deporte, nombre="Primera")
    campeonato = Campeonato.objects.create(
        nombre="Campeonato predictor",
        deporte=deporte,
        categoria=categoria,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
        creado_por=usuario,
    )
    equipo_local = Equipo.objects.create(
        campeonato=campeonato,
        nombre="Local predictor",
        facultad="Facultad A",
    )
    equipo_visitante = Equipo.objects.create(
        campeonato=campeonato,
        nombre="Visitante predictor",
        facultad="Facultad B",
    )
    ahora = timezone.now()

    for indice in range(5):
        partido = Partido.objects.create(
            campeonato=campeonato,
            equipo_local=equipo_local,
            equipo_visitante=equipo_visitante,
            fecha_hora=ahora + timedelta(days=indice),
            jornada=indice + 1,
            estado=Partido.Estado.FINALIZADO,
        )
        Resultado.objects.create(
            partido=partido,
            goles_local=indice % 3,
            goles_visitante=(indice + 1) % 3,
            registrado_por=usuario,
        )

    resultado_entrenamiento = PredictorResultados().entrenar(campeonato.pk)

    assert resultado_entrenamiento["partidos_entrenados"] == 5
    assert 0 <= resultado_entrenamiento["accuracy_training"] <= 1
    assert resultado_entrenamiento["modelo_guardado"] == str(predictor.MODEL_PATH)
    assert predictor.MODEL_PATH.exists()
