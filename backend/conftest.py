"""Solo para tests; no afecta producción ni desarrollo."""
import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def limpiar_cache_antes_de_cada_test():
    cache.clear()


@pytest.fixture(autouse=True)
def usar_hash_rapido_en_tests(settings):
    settings.PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]


@pytest.fixture(scope="session")
def _dir_modelos_ml(tmp_path_factory):
    return tmp_path_factory.mktemp("modelos_ml")


@pytest.fixture(autouse=True)
def modelo_ml_aislado(monkeypatch, _dir_modelos_ml):
    """Los tests entrenan/guardan el puntuador en una carpeta temporal, no en models_trained."""
    from apps.ml.services import asignacion_scorer

    monkeypatch.setattr(asignacion_scorer, "MODEL_DIR", _dir_modelos_ml)
    monkeypatch.setattr(asignacion_scorer, "MODEL_PATH", _dir_modelos_ml / "asignacion_scorer.joblib")


@pytest.fixture(autouse=True)
def _sin_servicios_externos(settings):
    """Las pruebas nunca llaman a Groq ni a Firebase aunque el .env local tenga credenciales reales."""
    settings.GROQ_API_KEY = ""
    settings.FCM_CREDENTIALS_FILE = ""
    settings.LLM_PROVIDER = "groq"      # sin clave equivale a reglas locales
    settings.STT_PROVIDER = "groq"
