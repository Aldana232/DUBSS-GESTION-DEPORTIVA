from datetime import datetime

from rest_framework import serializers

from apps.agente.models import AccionPendiente, ConversacionAgente, MensajeAgente
from apps.agente.services.herramientas import _fmt


class EntradaMensajeSerializer(serializers.Serializer):
    conversacion = serializers.IntegerField(required=False, allow_null=True)
    texto = serializers.CharField(min_length=2, max_length=1000, trim_whitespace=True)


def _lugar(x: dict) -> str:
    return f"{_fmt(datetime.fromisoformat(x['inicio']))} · {x['cancha'] or 'sin cancha'}"


class AccionSerializer(serializers.ModelSerializer):
    estado = serializers.SerializerMethodField()
    detalle = serializers.SerializerMethodField()

    class Meta:
        model = AccionPendiente
        fields = ["id", "herramienta", "estado", "resumen", "detalle", "resultado", "creado_en", "expira_en", "resuelta_en"]

    def get_estado(self, a):
        # La vigencia es exacta sin esperar a la tarea periódica.
        return AccionPendiente.Estado.EXPIRADA.value if a.vencida else a.estado

    def get_detalle(self, a):
        p = a.propuesta
        if a.herramienta == "aplicar_reprogramacion":
            cambios = p.get("cambios", [])
            return {
                "tipo": "reprogramacion", "motivo": p.get("motivo"), "clima_verificado": p.get("clima_verificado"),
                "cambios": [{"partido": c["partido"], "campeonato": c["campeonato"], "jornada": c["jornada"],
                             "antes": _lugar(c["anterior"]), "despues": _lugar(c["nuevo"]), "clima": c["nuevo"].get("clima")}
                            for c in cambios],
                "delegados": len({u for c in cambios for u in c["delegados"]}),
                "sin_solucion": [{"partido": s["partido"], "motivo": s["motivo"]} for s in p.get("sin_solucion", [])],
            }
        if a.herramienta == "enviar_notificacion":
            return {"tipo": "notificacion", "titulo": p.get("titulo"), "mensaje": p.get("mensaje"),
                    "destinatarios": len(p.get("usuarios", [])), "vista_previa": p.get("vista_previa", [])}
        return {}


class MensajeSerializer(serializers.ModelSerializer):
    acciones = AccionSerializer(many=True, read_only=True)

    class Meta:
        model = MensajeAgente
        fields = ["id", "rol", "contenido", "pasos", "descargas", "acciones", "creado_en"]


class ConversacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversacionAgente
        fields = ["id", "titulo", "creado_en", "actualizado_en"]
