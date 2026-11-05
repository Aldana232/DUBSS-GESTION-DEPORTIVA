from rest_framework import serializers

from apps.users.models import Usuario

from .models import Bitacora


class UsuarioBitacoraSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)

    class Meta:
        model = Usuario
        fields = ["id", "nombre_completo", "email"]


class BitacoraSerializer(serializers.ModelSerializer):
    usuario = UsuarioBitacoraSerializer(read_only=True)

    class Meta:
        model = Bitacora
        fields = [
            "id",
            "usuario",
            "usuario_email",
            "accion",
            "modulo",
            "objeto_id",
            "descripcion",
            "detalle",
            "resultado",
            "ip_origen",
            "fecha_hora",
        ]
        read_only_fields = fields
