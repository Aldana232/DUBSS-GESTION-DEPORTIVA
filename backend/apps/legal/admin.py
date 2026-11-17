from django.contrib import admin

from .models import AceptacionLegal


@admin.register(AceptacionLegal)
class AceptacionLegalAdmin(admin.ModelAdmin):
    """Solo lectura: es evidencia, no se corrige a mano."""
    list_display = ("usuario", "documento", "version", "aceptado_en", "ip_origen")
    list_filter = ("documento", "version")
    search_fields = ("usuario__email",)
    readonly_fields = [f.name for f in AceptacionLegal._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
