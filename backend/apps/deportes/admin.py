from django.contrib import admin
from .models import Facultad, Deporte, Categoria, Campeonato, Equipo, FichaJugador


@admin.register(Facultad)
class FacultadAdmin(admin.ModelAdmin):
    list_display = ["nombre", "sigla"]
    search_fields = ["nombre", "sigla"]


@admin.register(Deporte)
class DeporteAdmin(admin.ModelAdmin):
    list_display  = ["nombre", "activo", "creado_en"]
    list_filter   = ["activo"]
    search_fields = ["nombre"]


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display  = ["nombre", "deporte", "genero", "activa"]
    list_filter   = ["deporte", "genero", "activa"]


@admin.register(Campeonato)
class CampeonatoAdmin(admin.ModelAdmin):
    list_display  = ["nombre", "categoria", "estado", "fecha_inicio", "fecha_fin"]
    list_filter   = ["estado", "categoria", "formato"]
    search_fields = ["nombre"]
    date_hierarchy = "fecha_inicio"


class FichaJugadorInline(admin.TabularInline):
    model = FichaJugador
    extra = 0
    fields = ["nombre", "apellido", "carnet", "numero_camiseta", "posicion", "estado"]


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display  = ["nombre", "facultad", "estado", "delegado"]
    list_filter   = ["facultad", "estado"]
    search_fields = ["nombre", "facultad__nombre"]
    inlines       = [FichaJugadorInline]


@admin.register(FichaJugador)
class FichaJugadorAdmin(admin.ModelAdmin):
    list_display  = ["nombre", "apellido", "equipo", "numero_camiseta", "posicion", "estado"]
    list_filter   = ["posicion", "estado"]
    search_fields = ["nombre", "apellido", "carnet", "registro"]
