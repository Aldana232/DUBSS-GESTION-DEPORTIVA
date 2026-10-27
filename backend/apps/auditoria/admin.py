from django.contrib import admin

from .models import Bitacora


@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):
    list_display = ["fecha", "usuario_email", "accion", "entidad", "entidad_id", "resultado"]
    list_filter = ["accion", "entidad", "resultado"]
    search_fields = ["descripcion", "usuario_email"]
    date_hierarchy = "fecha"
    readonly_fields = [
        "id",
        "usuario",
        "usuario_email",
        "accion",
        "entidad",
        "entidad_id",
        "descripcion",
        "detalle",
        "resultado",
        "ip_address",
        "fecha",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
