"""Organizador y delegado comparten COORDINADOR hasta F1, cuando serán roles distintos.
Los roles finales serán SUPERADMIN, ADMIN_DUBSS, ORGANIZADOR y DELEGADO.
"""


def _esta_autenticado(user):
    return bool(user is not None and getattr(user, "is_authenticated", False))


def es_superadmin(user):
    return _esta_autenticado(user) and bool(getattr(user, "is_superuser", False))


def es_admin(user):
    return _esta_autenticado(user) and (
        getattr(user, "rol", None) == "ADMIN_DUBSS"
        or bool(getattr(user, "is_superuser", False))
    )


def es_organizador(user):
    return _esta_autenticado(user) and getattr(user, "rol", None) == "COORDINADOR"


def es_delegado(user):
    return _esta_autenticado(user) and getattr(user, "rol", None) == "COORDINADOR"


def es_arbitro(user):
    return _esta_autenticado(user) and getattr(user, "rol", None) == "ARBITRO"
