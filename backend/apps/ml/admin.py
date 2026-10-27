from django.contrib import admin
from .models import PrediccionPartido, RiesgoClimatico


@admin.register(PrediccionPartido)
class PrediccionAdmin(admin.ModelAdmin):
    list_display  = ["partido", "prob_victoria_local", "prob_empate",
                     "prob_victoria_visit", "confianza", "modelo_version"]
    list_filter   = ["modelo_version"]


@admin.register(RiesgoClimatico)
class RiesgoClimaticoAdmin(admin.ModelAdmin):
    list_display  = ["partido", "nivel_riesgo", "temperatura",
                     "precipitacion", "consultado_en"]
    list_filter   = ["nivel_riesgo"]
