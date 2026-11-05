from django.contrib import admin

from .models import Bitacora


@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):
    list_display = ["fecha_hora", "usuario_email", "accion", "modulo", "objeto_id", "resultado"]
    list_filter = ["accion", "modulo", "resultado"]
    search_fields = ["descripcion", "usuario_email"]
    date_hierarchy = "fecha_hora"
    readonly_fields = [
        "id",
        "usuario",
        "usuario_email",
        "accion",
        "modulo",
        "objeto_id",
        "descripcion",
        "detalle",
        "resultado",
        "ip_origen",
        "fecha_hora",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
