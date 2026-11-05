from django.contrib import admin

from apps.agente.models import AccionPendiente, ConversacionAgente, MensajeAgente


@admin.register(AccionPendiente)
class AccionPendienteAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "herramienta", "estado", "creado_en", "expira_en")
    list_filter = ("estado", "herramienta")
    readonly_fields = [f.name for f in AccionPendiente._meta.fields]


admin.site.register(ConversacionAgente)
admin.site.register(MensajeAgente)
