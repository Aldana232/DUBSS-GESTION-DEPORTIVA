"""
apps/users/permissions.py
Permisos basados en roles del sistema DUBSS.
"""
from rest_framework.permissions import BasePermission
from .roles import es_admin, es_arbitro, es_organizador


class EsAdminDUBSS(BasePermission):
    """Solo el administrador DUBSS puede acceder."""
    message = "Requiere rol de Administrador DUBSS."

    def has_permission(self, request, view):
        return es_admin(request.user)


class EsCoordinadorOAdmin(BasePermission):
    """Coordinador de facultad o administrador."""
    message = "Requiere rol de Coordinador o Administrador DUBSS."

    def has_permission(self, request, view):
        return es_admin(request.user) or es_organizador(request.user)


class EsArbitroOAdmin(BasePermission):
    """Árbitro o administrador (para registro de resultados)."""
    message = "Requiere rol de Árbitro o Administrador DUBSS."

    def has_permission(self, request, view):
        return es_admin(request.user) or es_arbitro(request.user)


class EsDeportistaPropioOAdmin(BasePermission):
    """Un deportista solo puede ver/editar su propio perfil; admin puede todo."""

    def has_object_permission(self, request, view, obj):
        return es_admin(request.user) or obj == request.user


class EsLecturaPublica(BasePermission):
    """GET permitido para todos; escritura solo para autenticados."""

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user and request.user.is_authenticated
