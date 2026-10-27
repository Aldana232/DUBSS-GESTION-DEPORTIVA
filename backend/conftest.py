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
