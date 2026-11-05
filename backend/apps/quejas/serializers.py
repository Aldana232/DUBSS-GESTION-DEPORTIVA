from rest_framework import serializers

from apps.users.roles import es_delegado
from .models import Queja


class QuejaSerializer(serializers.ModelSerializer):
    encuentro_detalle = serializers.SerializerMethodField()
    delegado_nombre = serializers.CharField(source="delegado.nombre_completo", read_only=True, default=None)

    def get_encuentro_detalle(self, obj) -> dict:
        p = obj.encuentro
        return {
            "id": p.pk,
            "local": p.equipo_local.nombre if p.equipo_local_id else "Por definir",
            "visitante": p.equipo_visitante.nombre if p.equipo_visitante_id else "Por definir",
            "fecha_hora": p.fecha_hora,
            "campeonato": p.campeonato.nombre,
        }

    class Meta:
        model = Queja
        fields = [
            "id",
            "tipo",
            "descripcion",
            "estado",
            "resolucion",
            "fecha_hora",
            "resuelta_en",
            "admin_resuelve",
            "delegado",
            "delegado_nombre",
            "encuentro",
            "encuentro_detalle",
        ]
        read_only_fields = [
            "id",
            "estado",
            "resolucion",
            "fecha_hora",
            "resuelta_en",
            "admin_resuelve",
            "delegado",
        ]

    def validate_encuentro(self, encuentro):
        if es_delegado(self.context["request"].user):
            if not encuentro.campeonato.inscripciones.filter(
                equipo__facultad_id=self.context["request"].user.facultad_id,
                estado="APROBADA",
            ).exists():
                raise serializers.ValidationError(
                    "Solo puedes presentar quejas sobre partidos de equipos de tu facultad."
                )
        return encuentro

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["delegado"] = request.user
        return super().create(validated_data)
