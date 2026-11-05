"""
apps/reportes/equipo_jugador.py
RF16/RF17 — Reportes por equipo y por jugador, en PDF y Excel.
"""
import io
import re

from django.db.models import Count, Q
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from apps.deportes.models import Equipo, FichaJugador
from apps.fixture.models import Incidencia, Partido
from apps.users.permissions import EsAdminUOrganizador

ROJO = "d21115"
Seccion = tuple[str, list[str], list[list]]


def _archivo(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", texto).strip("_") or "reporte"


def _pdf(titulo: str, subtitulo: str, secciones: list[Seccion]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    estilos = getSampleStyleSheet()
    historia = [
        Paragraph("DUBSS — UAGRM", estilos["Title"]),
        Paragraph(titulo, estilos["Heading1"]),
        Paragraph(subtitulo, estilos["Normal"]),
        Spacer(1, 0.25 * inch),
    ]
    for nombre, cabecera, filas in secciones:
        historia.append(Paragraph(nombre, estilos["Heading2"]))
        if not filas:
            historia.append(Paragraph("Sin registros.", estilos["Normal"]))
        else:
            tabla = Table([cabecera] + [[str(c) for c in f] for f in filas], repeatRows=1)
            tabla.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(f"#{ROJO}")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ]))
            historia.append(tabla)
        historia.append(Spacer(1, 0.2 * inch))
    SimpleDocTemplate(buf, pagesize=letter).build(historia)
    return buf.getvalue()


def _excel(secciones: list[Seccion]) -> bytes:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill

    libro = openpyxl.Workbook()
    libro.remove(libro.active)
    relleno = PatternFill("solid", fgColor=ROJO)
    for nombre, cabecera, filas in secciones:
        hoja = libro.create_sheet(nombre[:31])
        for col, texto in enumerate(cabecera, 1):
            celda = hoja.cell(row=1, column=col, value=texto)
            celda.fill = relleno
            celda.font = Font(bold=True, color="FFFFFF")
            celda.alignment = Alignment(horizontal="center")
            hoja.column_dimensions[celda.column_letter].width = max(14, len(texto) + 4)
        for fila in filas:
            hoja.append(list(fila))
    buf = io.BytesIO()
    libro.save(buf)
    return buf.getvalue()


def _responder(request, formato, base, titulo, subtitulo, secciones, modulo, objeto_id):
    if formato == "pdf":
        contenido, tipo, ext = _pdf(titulo, subtitulo, secciones), "application/pdf", "pdf"
    else:
        contenido = _excel(secciones)
        tipo = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    registrar(
        Bitacora.Accion.EXPORTAR,
        request=request,
        modulo=modulo,
        objeto_id=objeto_id,
        descripcion=f"Reporte de {modulo} exportado.",
        detalle={"formato": formato.upper()},
    )
    respuesta = HttpResponse(contenido, content_type=tipo)
    respuesta["Content-Disposition"] = f'attachment; filename="{_archivo(base)}.{ext}"'
    return respuesta


def _fmt_resultado(partido):
    resultado = getattr(partido, "resultado", None)
    return f"{resultado.goles_local} - {resultado.goles_visitante}" if resultado else "Pendiente"


@extend_schema(tags=["reportes"])
class ReporteEquipoView(APIView):
    """RF16 — Plantel y partidos de un equipo."""
    permission_classes = [EsAdminUOrganizador]
    formato = "pdf"

    def get(self, request, equipo_id):
        try:
            equipo = Equipo.objects.select_related("facultad").get(pk=equipo_id)
        except Equipo.DoesNotExist:
            return Response({"error": "Equipo no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        plantel = FichaJugador.objects.filter(equipo=equipo, estado="ACTIVO").annotate(
            goles=Count("incidencias", filter=Q(incidencias__tipo=Incidencia.Tipo.GOL)),
            amarillas=Count("incidencias", filter=Q(incidencias__tipo=Incidencia.Tipo.TARJETA_AMARILLA)),
            rojas=Count("incidencias", filter=Q(incidencias__tipo=Incidencia.Tipo.TARJETA_ROJA)),
        ).order_by("numero_camiseta", "apellido")
        partidos = (
            Partido.objects.filter(Q(equipo_local=equipo) | Q(equipo_visitante=equipo))
            .select_related("equipo_local", "equipo_visitante", "campeonato", "resultado")
            .order_by("fecha_hora")
        )
        secciones: list[Seccion] = [
            ("Plantel", ["N°", "Jugador", "Posición", "Goles", "Amarillas", "Rojas", "Sanción"], [
                [j.numero_camiseta if j.numero_camiseta is not None else "-",
                 f"{j.nombre} {j.apellido}", j.posicion, j.goles, j.amarillas, j.rojas,
                 j.partidos_sancion_restantes] for j in plantel
            ]),
            ("Partidos", ["Campeonato", "Jornada", "Local", "Resultado", "Visitante", "Fecha", "Estado"], [
                [p.campeonato.nombre, p.jornada,
                 p.equipo_local.nombre if p.equipo_local else "Por definir",
                 _fmt_resultado(p),
                 p.equipo_visitante.nombre if p.equipo_visitante else "Por definir",
                 p.fecha_hora.strftime("%d/%m/%Y %H:%M"), p.estado] for p in partidos
            ]),
        ]
        return _responder(
            request, self.formato, f"equipo_{equipo.nombre}", f"Equipo: {equipo.nombre}",
            f"Facultad: {equipo.facultad.nombre}", secciones, "equipo", equipo.pk,
        )


@extend_schema(tags=["reportes"])
class ReporteJugadorView(APIView):
    """RF16 — Ficha y estadísticas de un jugador."""
    permission_classes = [EsAdminUOrganizador]
    formato = "pdf"

    def get(self, request, jugador_id):
        try:
            jugador = FichaJugador.objects.select_related("equipo__facultad").get(pk=jugador_id)
        except FichaJugador.DoesNotExist:
            return Response({"error": "Jugador no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        incidencias = (
            Incidencia.objects.filter(jugador=jugador)
            .select_related("partido__equipo_local", "partido__equipo_visitante")
            .order_by("partido__fecha_hora", "minuto")
        )
        conteo = {t: 0 for t in Incidencia.Tipo.values}
        for i in incidencias:
            conteo[i.tipo] += 1
        secciones: list[Seccion] = [
            ("Resumen", ["Dato", "Valor"], [
                ["Jugador", f"{jugador.nombre} {jugador.apellido}"],
                ["Equipo", jugador.equipo.nombre],
                ["Facultad", jugador.equipo.facultad.nombre],
                ["Posición", jugador.posicion],
                ["Camiseta", jugador.numero_camiseta if jugador.numero_camiseta is not None else "-"],
                ["Goles", conteo[Incidencia.Tipo.GOL]],
                ["Tarjetas amarillas", conteo[Incidencia.Tipo.TARJETA_AMARILLA]],
                ["Tarjetas rojas", conteo[Incidencia.Tipo.TARJETA_ROJA]],
                ["Partidos de sanción pendientes", jugador.partidos_sancion_restantes],
            ]),
            ("Incidencias", ["Fecha", "Partido", "Tipo", "Minuto"], [
                [i.partido.fecha_hora.strftime("%d/%m/%Y"),
                 f"{i.partido.equipo_local or 'Por definir'} vs {i.partido.equipo_visitante or 'Por definir'}",
                 i.get_tipo_display(), i.minuto if i.minuto is not None else "-"] for i in incidencias
            ]),
        ]
        return _responder(
            request, self.formato, f"jugador_{jugador.apellido}_{jugador.nombre}",
            f"Jugador: {jugador.nombre} {jugador.apellido}", f"Equipo: {jugador.equipo.nombre}",
            secciones, "jugador", jugador.pk,
        )


class ReporteEquipoExcelView(ReporteEquipoView):
    formato = "excel"


class ReporteJugadorExcelView(ReporteJugadorView):
    formato = "excel"


@extend_schema(tags=["reportes"])
class ReporteFacultadView(APIView):
    """F6-05 — Rendimiento de los equipos de una facultad en todos sus campeonatos."""
    permission_classes = [EsAdminUOrganizador]
    formato = "pdf"

    def get(self, request, facultad_id):
        from apps.deportes.models import Facultad
        from apps.reportes.estadisticas import estadisticas_facultad

        try:
            facultad = Facultad.objects.get(pk=facultad_id)
        except Facultad.DoesNotExist:
            return Response({"error": "Facultad no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        d = estadisticas_facultad(facultad)
        t = d["totales"]
        secciones: list[Seccion] = [
            ("Resumen", ["Dato", "Valor"], [
                ["Facultad", f"{facultad.nombre} ({facultad.sigla})"], ["Equipos", t["equipos"]], ["Jugadores", t["jugadores"]],
                ["Partidos jugados", t["pj"]], ["Ganados / empatados / perdidos", f"{t['pg']} / {t['pe']} / {t['pp']}"],
                ["Goles a favor / en contra", f"{t['gf']} / {t['gc']}"], ["Tarjetas amarillas", t["amarillas"]],
                ["Tarjetas rojas", t["rojas"]], ["Campeonatos", ", ".join(d["campeonatos"]) or "—"],
            ]),
            ("Equipos", ["Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DG", "Pts"],
             [[e["equipo"], e["pj"], e["pg"], e["pe"], e["pp"], e["gf"], e["gc"], e["dg"], e["puntos"]] for e in d["equipos"]]),
            ("Goleadores", ["Jugador", "Equipo", "Goles"], [[g["jugador"], g["equipo"], g["goles"]] for g in d["goleadores"]]),
        ]
        return _responder(request, self.formato, f"facultad_{facultad.sigla}", f"Facultad: {facultad.nombre}",
                          "Rendimiento deportivo en todos los campeonatos", secciones, "facultad", facultad.pk)


class ReporteFacultadExcelView(ReporteFacultadView):
    formato = "excel"


@extend_schema(tags=["reportes"])
class EstadisticasFacultadView(APIView):
    """F6-05 — Las mismas estadísticas de la facultad en JSON, para mostrarlas en pantalla."""
    permission_classes = [EsAdminUOrganizador]

    def get(self, request, facultad_id):
        from apps.deportes.models import Facultad
        from apps.reportes.estadisticas import estadisticas_facultad

        try:
            facultad = Facultad.objects.get(pk=facultad_id)
        except Facultad.DoesNotExist:
            return Response({"error": "Facultad no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        return Response(estadisticas_facultad(facultad))
