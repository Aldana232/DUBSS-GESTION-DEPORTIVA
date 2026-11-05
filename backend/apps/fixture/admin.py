from django.contrib import admin
from .models import Partido, Resultado, Incidencia, TablaPosiciones, PosicionHistorial


class ResultadoInline(admin.StackedInline):
    model  = Resultado
    extra  = 0
    fields = ["goles_local", "goles_visitante", "penales_local", "penales_visitante",
              "walkover", "verificado", "observaciones"]


class IncidenciaInline(admin.TabularInline):
    model  = Incidencia
    extra  = 0
    fields = ["tipo", "jugador", "minuto", "descripcion"]


@admin.register(Partido)
class PartidoAdmin(admin.ModelAdmin):
    list_display  = ["__str__", "campeonato", "jornada", "estado", "cancha"]
    list_filter   = ["campeonato", "estado", "jornada"]
    search_fields = ["equipo_local__nombre", "equipo_visitante__nombre"]
    date_hierarchy = "fecha_hora"
    inlines        = [ResultadoInline, IncidenciaInline]


@admin.register(TablaPosiciones)
class TablaPosicionesAdmin(admin.ModelAdmin):
    list_display = ["posicion", "equipo", "campeonato", "pj", "pg", "pe", "pp", "gf", "gc", "puntos"]
    list_filter  = ["campeonato"]
    ordering     = ["posicion", "-puntos"]


@admin.register(PosicionHistorial)
class PosicionHistorialAdmin(admin.ModelAdmin):
    list_display = ["campeonato", "jornada", "posicion", "equipo", "puntos"]
    list_filter  = ["campeonato", "jornada"]
