"""Validaciones reutilizables de serializers."""


class RangoPosteriorMixin:
    """
    Exige que el campo final sea posterior al inicial (en altas y en ediciones parciales).

        class HorarioSerializer(RangoPosteriorMixin, serializers.ModelSerializer):
            rango_inicio, rango_fin = "hora_inicio", "hora_fin"
            rango_mensaje = "La hora de fin debe ser posterior al inicio."
    """
    rango_inicio = "hora_inicio"
    rango_fin = "hora_fin"
    rango_mensaje = "La hora de fin debe ser posterior al inicio."

    def validate(self, attrs):
        from rest_framework import serializers

        attrs = super().validate(attrs)
        inicio = attrs.get(self.rango_inicio, getattr(self.instance, self.rango_inicio, None))
        fin = attrs.get(self.rango_fin, getattr(self.instance, self.rango_fin, None))
        if inicio is not None and fin is not None and fin <= inicio:
            raise serializers.ValidationError({self.rango_fin: self.rango_mensaje})
        return attrs
