"""
apps/deportes/mi_ficha.py
F7-10 — Panel del jugador con cuenta. Solo lectura: su ficha, sus estadísticas, su sanción y sus partidos.
Una cuenta de jugador solo ve las fichas vinculadas a ella (FichaJugador.usuario).
"""
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.deportes.models import Campeonato, FichaJugador
from apps.fixture.models import Partido
from apps.reportes.estadisticas import estadisticas_jugador
from apps.users.permissions import EsJugador

LIMITE = 5


def _del_equipo(equipo_id: int) -> Q:
    return Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)


def _proximos(equipo_id: int) -> list[dict]:
    qs = (Partido.objects.filter(_del_equipo(equipo_id), estado=Partido.Estado.PROGRAMADO, fecha_hora__gte=timezone.now(),
                                 campeonato__estado=Campeonato.Estado.EN_CURSO, equipo_local__isnull=False, equipo_visitante__isnull=False)
          .select_related("equipo_local", "equipo_visitante", "cancha", "campeonato").order_by("fecha_hora")[:LIMITE])
    filas = []
    for p in qs:
        es_local = p.equipo_local_id == equipo_id
        rival = p.equipo_visitante if es_local else p.equipo_local
        filas.append({"id": p.pk, "fecha_hora": p.fecha_hora, "rival": rival.nombre, "es_local": es_local,
                      "cancha": p.cancha.nombre if p.cancha_id else None, "campeonato": p.campeonato.nombre, "jornada": p.jornada})
    return filas


def _ultimos(equipo_id: int) -> list[dict]:
    qs = (Partido.objects.filter(_del_equipo(equipo_id), estado=Partido.Estado.FINALIZADO, resultado__isnull=False)
          .select_related("equipo_local", "equipo_visitante", "resultado", "campeonato").order_by("-fecha_hora")[:LIMITE])
    filas = []
    for p in qs:
        es_local = p.equipo_local_id == equipo_id
        rival = p.equipo_visitante if es_local else p.equipo_local
        gf, gc = ((p.resultado.goles_local, p.resultado.goles_visitante) if es_local else (p.resultado.goles_visitante, p.resultado.goles_local))
        filas.append({"id": p.pk, "fecha_hora": p.fecha_hora, "rival": rival.nombre, "marcador": f"{gf}-{gc}",
                      "resultado": "G" if gf > gc else "E" if gf == gc else "P", "campeonato": p.campeonato.nombre})
    return filas


@extend_schema(tags=["deportes"], summary="F7-10 — Mi ficha de jugador (solo lectura)")
class MiFichaView(APIView):
    permission_classes = [EsJugador]

    def get(self, request):
        fichas = FichaJugador.objects.filter(usuario=request.user).select_related("equipo__facultad").order_by("equipo__nombre")
        datos = []
        for f in fichas:
            e = f.equipo
            datos.append({
                "id": f.pk, "nombre": f.nombre, "apellido": f.apellido, "numero": f.numero_camiseta, "posicion": f.posicion, "estado": f.estado,
                "equipo": {"id": e.pk, "nombre": e.nombre, "color": e.color, "facultad": e.facultad.nombre, "sigla": e.facultad.sigla},
                "estadisticas": estadisticas_jugador(f),
                "sancion": {"partidos_restantes": f.partidos_sancion_restantes,
                            "mensaje": (f"Suspendido: te quedan {f.partidos_sancion_restantes} partido(s) sin poder jugar."
                                        if f.partidos_sancion_restantes else None)},
                "proximos_partidos": _proximos(e.pk), "ultimos_resultados": _ultimos(e.pk),
            })
        return Response({"fichas": datos})
