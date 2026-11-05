"""
apps/users/permissions.py
Permisos basados en roles del sistema DUBSS.
"""
from rest_framework.permissions import BasePermission
from .roles import es_admin, es_delegado, es_jugador, es_organizador, es_superadmin


def _delegado_pertenece_a_facultad(user, obj):
    if not es_delegado(user) or user.facultad_id is None:
        return False
    facultad_id = getattr(obj, "facultad_id", None)
    if facultad_id is None:
        equipo = getattr(obj, "equipo", None)
        facultad_id = getattr(equipo, "facultad_id", None)
    return facultad_id == user.facultad_id


class EsSuperadmin(BasePermission):
    """Solo el superadministrador puede acceder."""
    message = "Requiere rol de Superadministrador."

    def has_permission(self, request, view):
        return es_superadmin(request.user)


class EsAdmin(BasePermission):
    """Administrador DUBSS o superadministrador."""
    message = "Requiere rol de Administrador DUBSS."

    def has_permission(self, request, view):
        return es_admin(request.user)


class EsAdminUOrganizador(BasePermission):
    """Administrador DUBSS o organizador."""
    message = "Requiere rol de Administrador DUBSS u Organizador."

    def has_permission(self, request, view):
        return es_admin(request.user) or es_organizador(request.user)


class EsJugador(BasePermission):
    """F7-10 - Jugador con cuenta: solo lectura de su propia ficha (no tiene ningun otro permiso)."""
    message = "Requiere rol de Jugador."

    def has_permission(self, request, view):
        return es_jugador(request.user)


class EsDelegado(BasePermission):
    """Solo delegados."""

    message = "Requiere rol de Delegado."

    def has_permission(self, request, view):
        return es_delegado(request.user)


class EsAdminUOrganizadorLectura(BasePermission):
    """Administrador u organizador, sin permisos de escritura."""

    def has_permission(self, request, view):
        return es_admin(request.user) or es_organizador(request.user)


class EsAdminUOrganizadorODelegado(BasePermission):
    """Roles que pueden consultar recursos de gestión."""

    def has_permission(self, request, view):
        return (
            es_admin(request.user)
            or es_organizador(request.user)
            or es_delegado(request.user)
        )


class DelegadoDeSuFacultad(BasePermission):
    """Comprueba que el objeto pertenezca a la facultad del delegado."""

    def has_object_permission(self, request, view, obj):
        return _delegado_pertenece_a_facultad(request.user, obj)


class EsAdminODelegadoDeSuFacultad(BasePermission):
    """Administrador o delegado limitado a los objetos de su facultad."""

    def has_permission(self, request, view):
        return es_admin(request.user) or es_delegado(request.user)

    def has_object_permission(self, request, view, obj):
        return es_admin(request.user) or _delegado_pertenece_a_facultad(
            request.user,
            obj,
        )


class EsAdminOrganizadorODelegado(BasePermission):
    """Compatibilidad: administrador, organizador o delegado."""

    def has_permission(self, request, view):
        return (
            es_admin(request.user)
            or es_organizador(request.user)
            or es_delegado(request.user)
        )


class EsCuentaConPanel(BasePermission):
    """Cualquier rol con cuenta activa (incluido el jugador): ver y editar SU PROPIA cuenta. No da acceso a datos de otros."""
    message = "Esta cuenta no tiene acceso."

    def has_permission(self, request, view):
        return (es_admin(request.user) or es_organizador(request.user) or es_delegado(request.user) or es_jugador(request.user))


class EsUsuarioOperativo(BasePermission):
    """Cualquier rol activo del sistema, excepto el rol reservado JUGADOR."""
    message = "El rol de esta cuenta no tiene permisos de escritura."

    def has_permission(self, request, view):
        return (
            es_admin(request.user)
            or es_organizador(request.user)
            or es_delegado(request.user)
        )


class SoloLecturaPublica(BasePermission):
    """Permite solo operaciones de lectura, también a visitantes anónimos."""

    def has_permission(self, request, view):
        return request.method in ("GET", "HEAD", "OPTIONS")


class EsLecturaPublica(SoloLecturaPublica):
    """Alias compatible para endpoints de lectura pública."""
