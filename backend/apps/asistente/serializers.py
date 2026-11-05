from rest_framework import serializers

from apps.asistente.services.intents import FORMATOS, INTENCIONES
from apps.deportes.models import Campeonato, Equipo, FichaJugador


class InterpretarSerializer(serializers.Serializer):
    texto = serializers.CharField(min_length=3, max_length=500, trim_whitespace=True)
    # Seguimiento de una aclaración: se conserva lo que ya se había entendido.
    previo = serializers.DictField(required=False)
    seleccion = serializers.DictField(child=serializers.IntegerField(), required=False)

    def validate_previo(self, valor):
        if valor.get("intencion") not in INTENCIONES:
            raise serializers.ValidationError("La intención anterior no es válida.")
        if valor.get("formato") not in (None, *FORMATOS):
            raise serializers.ValidationError("Formato no válido.")
        return {"intencion": valor["intencion"], "formato": valor.get("formato"),
                "proveedor": str(valor.get("proveedor", "reglas"))[:10]}

    def validate_seleccion(self, valor):
        return {k: v for k, v in valor.items() if k in ("campeonato", "equipo", "jugador")}


class EjecutarSerializer(serializers.Serializer):
    """La orden confirmada: intención de la lista blanca + ids ya resueltos. Todo se vuelve a validar aquí."""
    intencion = serializers.ChoiceField(choices=list(INTENCIONES))
    formato = serializers.ChoiceField(choices=list(FORMATOS), required=False, allow_null=True)
    campeonato = serializers.PrimaryKeyRelatedField(queryset=Campeonato.objects.all(), required=False, allow_null=True)
    equipo = serializers.PrimaryKeyRelatedField(queryset=Equipo.objects.all(), required=False, allow_null=True)
    jugador = serializers.PrimaryKeyRelatedField(queryset=FichaJugador.objects.all(), required=False, allow_null=True)

    def validate(self, datos):
        faltan = [c for c in INTENCIONES[datos["intencion"]]["requiere"] if not datos.get(c)]
        if faltan:
            raise serializers.ValidationError({c: "Este dato es obligatorio para la orden." for c in faltan})
        return datos
