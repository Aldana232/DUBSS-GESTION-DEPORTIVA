"""Helpers únicos para consultar los roles institucionales del usuario."""


def _esta_autenticado(user):
    return bool(user is not None and getattr(user, "is_authenticated", False))


def es_superadmin(user):
    return _esta_autenticado(user) and (
        getattr(user, "rol", None) == "SUPERADMIN"
        or bool(getattr(user, "is_superuser", False))
    )


def es_admin(user):
    return _esta_autenticado(user) and (
        getattr(user, "rol", None) in {"ADMIN_DUBSS", "SUPERADMIN"}
        or bool(getattr(user, "is_superuser", False))
    )


def es_organizador(user):
    return _esta_autenticado(user) and getattr(user, "rol", None) == "ORGANIZADOR"


def es_jugador(user):
    return _esta_autenticado(user) and getattr(user, "rol", None) == "JUGADOR"


def es_delegado(user):
    return _esta_autenticado(user) and getattr(user, "rol", None) == "DELEGADO"
