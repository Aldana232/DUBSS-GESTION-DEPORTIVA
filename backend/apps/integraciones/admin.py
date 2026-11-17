from django.contrib import admin

from .models import EventoSaliente


@admin.register(EventoSaliente)
class EventoSalienteAdmin(admin.ModelAdmin):
    list_display = ("tipo", "estado", "intentos", "creado", "entregado_en")
    list_filter = ("estado", "tipo")
    readonly_fields = [f.name for f in EventoSaliente._meta.fields]

    def has_add_permission(self, request):
        return False
