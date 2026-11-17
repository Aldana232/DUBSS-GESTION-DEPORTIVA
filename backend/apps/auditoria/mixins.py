"""Registro en la bitácora de las altas, ediciones y bajas de un recurso (evita repetir el mismo molde en cada vista)."""
from .models import Bitacora
from .services import registrar


class AuditaCrudMixin:
    """
    Para un ModelViewSet / ListCreateAPIView. Declara:

        auditoria_modulo = "equipo"
        auditoria_textos = {"crear": "Equipo creado.", "editar": "Equipo actualizado.", "eliminar": "Equipo eliminado."}

    Solo se audita lo que tenga texto: si falta «editar» o «eliminar», esa operación se hace sin registro, como antes.
    Ganchos opcionales: `datos_al_crear()` (campos extra para `serializer.save`) y `completar_edicion(obj)`
    (se ejecuta tras guardar y antes de auditar).
    """
    auditoria_modulo = ""
    auditoria_textos: dict[str, str] = {}

    def datos_al_crear(self) -> dict:
        return {}

    def completar_edicion(self, obj) -> None:
        return None

    def _auditar(self, accion, clave: str, obj) -> None:
        texto = self.auditoria_textos.get(clave)
        if texto:
            registrar(accion, request=self.request, modulo=self.auditoria_modulo, objeto_id=obj.pk, descripcion=texto)

    def perform_create(self, serializer):
        obj = serializer.save(**self.datos_al_crear())
        self._auditar(Bitacora.Accion.CREAR, "crear", obj)

    def perform_update(self, serializer):
        obj = serializer.save()
        self.completar_edicion(obj)
        self._auditar(Bitacora.Accion.EDITAR, "editar", obj)

    def perform_destroy(self, instance):
        self._auditar(Bitacora.Accion.ELIMINAR, "eliminar", instance)
        instance.delete()
