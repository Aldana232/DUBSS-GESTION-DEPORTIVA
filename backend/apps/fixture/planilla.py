"""
apps/fixture/planilla.py
F7-05 — Paquete de datos para trabajar la planilla sin conexión.

Con una sola consulta el celular descarga los partidos de hoy (y de los próximos días) con las plantillas de ambos
equipos y lo ya registrado. Así, en la cancha, la planilla funciona aunque no haya señal.
"""
from datetime import datetime, time, timedelta

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from apps.deportes.models import Campeonato, FichaJugador
from apps.fixture.models import Partido
from apps.fixture.services import sanciones
from apps.users.permissions import EsAdminUOrganizador

ESTADOS_VISIBLES = [Partido.Estado.PROGRAMADO, Partido.Estado.EN_CURSO, Partido.Estado.FINALIZADO]
MAX_PARTIDOS = 60


def _jugador(f: FichaJugador, partido: Partido) -> dict:
    # Un jugador sancionado no puede actuar; si la sanción nació en ESTE partido (tarjeta roja de hoy) sí figura.
    sancionado = f.partidos_sancion_restantes > 0 and not sanciones.sancion_proviene_del_partido(f, partido)
    return {"id": f.pk, "nombre": f.nombre, "apellido": f.apellido, "numero": f.numero_camiseta,
            "posicion": f.posicion, "sancionado": sancionado, "partidos_sancion": f.partidos_sancion_restantes if sancionado else 0}


def _equipo(equipo, partido: Partido, plantillas: dict) -> dict:
    return {"id": equipo.pk, "nombre": equipo.nombre, "color": equipo.color,
            "jugadores": [_jugador(f, partido) for f in plantillas.get(equipo.pk, [])]}


@extend_schema(tags=["fixture"], summary="F7-05 — Paquete de la planilla para trabajar sin conexión",
               parameters=[OpenApiParameter("dias", int, description="Cuántos días incluir desde hoy (1 a 3, por defecto 2).")])
class PaquetePlanillaView(APIView):
    permission_classes = [EsAdminUOrganizador]

    def get(self, request):
        try:
            dias = max(1, min(3, int(request.query_params.get("dias", 2))))
        except ValueError:
            dias = 2
        hoy = timezone.localdate()
        desde = timezone.make_aware(datetime.combine(hoy, time.min))
        hasta = desde + timedelta(days=dias)
        partidos = list(
            Partido.objects.filter(
                fecha_hora__gte=desde, fecha_hora__lt=hasta, estado__in=ESTADOS_VISIBLES,
                campeonato__estado=Campeonato.Estado.EN_CURSO, equipo_local__isnull=False, equipo_visitante__isnull=False,
            ).select_related("campeonato", "equipo_local", "equipo_visitante", "cancha", "resultado")
            .prefetch_related("incidencias__jugador").order_by("fecha_hora")[:MAX_PARTIDOS]
        )
        equipos = {e.pk for p in partidos for e in (p.equipo_local, p.equipo_visitante)}
        plantillas: dict[int, list] = {}
        for f in FichaJugador.objects.filter(equipo_id__in=equipos, estado="ACTIVO").order_by("numero_camiseta", "apellido"):
            plantillas.setdefault(f.equipo_id, []).append(f)

        datos = []
        for p in partidos:
            res = getattr(p, "resultado", None)
            datos.append({
                "id": p.pk, "jornada": p.jornada, "fase": p.fase, "estado": p.estado,
                "fecha_hora": timezone.localtime(p.fecha_hora).isoformat(), "duracion_min": p.duracion_min,
                "campeonato": {"id": p.campeonato_id, "nombre": p.campeonato.nombre, "formato": p.campeonato.formato},
                "cancha": p.cancha.nombre if p.cancha_id else None,
                "local": _equipo(p.equipo_local, p, plantillas), "visitante": _equipo(p.equipo_visitante, p, plantillas),
                "incidencias": [{"id": i.pk, "tipo": i.tipo, "jugador": i.jugador_id, "minuto": i.minuto, "descripcion": i.descripcion}
                                for i in p.incidencias.all()],
                "resultado": {"goles_local": res.goles_local, "goles_visitante": res.goles_visitante,
                              "penales_local": res.penales_local, "penales_visitante": res.penales_visitante} if res else None,
            })
        return Response({"generado_en": timezone.now().isoformat(), "usuario": request.user.pk, "partidos": datos})
