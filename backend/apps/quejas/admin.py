from django.contrib import admin

from .models import Queja


@admin.register(Queja)
class QuejaAdmin(admin.ModelAdmin):
    list_display = ["tipo", "estado", "encuentro", "delegado", "fecha_hora"]
    list_filter = ["tipo", "estado"]
    search_fields = ["descripcion", "resolucion", "delegado__email"]
    readonly_fields = ["fecha_hora", "resuelta_en"]
