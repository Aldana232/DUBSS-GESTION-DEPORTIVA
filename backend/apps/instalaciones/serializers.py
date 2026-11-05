from rest_framework import serializers
from .models import Instalacion, Cancha, BloqueoCancha, HorarioCancha


class InstalacionSerializer(serializers.ModelSerializer):
    total_canchas = serializers.SerializerMethodField()

    class Meta:
        model  = Instalacion
        fields = [
            "id", "nombre", "tipo", "ubicacion", "capacidad", "estado",
            "imagen", "total_canchas",
        ]
        read_only_fields = ["id"]

    def get_total_canchas(self, obj):
        return obj.canchas.filter(activa=True).count()


class CanchaSerializer(serializers.ModelSerializer):
    instalacion_nombre = serializers.CharField(source="instalacion.nombre", read_only=True)
    deporte_nombre     = serializers.CharField(source="deporte.nombre",     read_only=True)

    class Meta:
        model  = Cancha
        fields = ["id", "instalacion", "instalacion_nombre", "nombre",
                  "deporte", "deporte_nombre", "superficie", "capacidad",
                  "techada", "activa", "observaciones"]
        read_only_fields = ["id"]


class BloqueoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = BloqueoCancha
        fields = ["id", "cancha", "fecha_inicio", "fecha_fin",
                  "tipo", "motivo", "creado_por", "creado_en"]
        read_only_fields = ["id", "creado_por", "creado_en"]

    def create(self, validated_data):
        validated_data["creado_por"] = self.context["request"].user
        return super().create(validated_data)

    def validate(self, attrs):
        inicio = attrs.get("fecha_inicio", getattr(self.instance, "fecha_inicio", None))
        fin = attrs.get("fecha_fin", getattr(self.instance, "fecha_fin", None))
        if inicio is not None and fin is not None and fin <= inicio:
            raise serializers.ValidationError(
                {"fecha_fin": "La fecha de fin debe ser posterior al inicio."}
            )
        return attrs


class HorarioCanchaSerializer(serializers.ModelSerializer):
    class Meta:
        model = HorarioCancha
        fields = ["id", "cancha", "dia_semana", "hora_inicio", "hora_fin"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        inicio = attrs.get("hora_inicio", getattr(self.instance, "hora_inicio", None))
        fin = attrs.get("hora_fin", getattr(self.instance, "hora_fin", None))
        if inicio is not None and fin is not None and fin <= inicio:
            raise serializers.ValidationError(
                {"hora_fin": "La hora de fin debe ser posterior al inicio."}
            )
        return attrs
