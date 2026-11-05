"""
apps/agente/services/herramientas.py
F7-01 — Registro de herramientas tipadas del agente.

Reglas (del plan):
* Cada herramienta aplica los MISMOS permisos de la persona que habla con el agente.
* Los parámetros se validan con serializers de DRF; no existe SQL libre ni acceso genérico a la base.
* Las herramientas de lectura y cálculo se ejecutan; las de ESCRITURA solo crean una acción pendiente que una
  persona debe confirmar (ver `acciones.py`). El modelo nunca escribe datos por sí mismo.
* Lo que devuelven es DATO, nunca instrucción: el texto que viene de la base se limpia y se entrega marcado como tal.
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from apps.agente.models import AccionPendiente, ConversacionAgente, PropuestaAgente
from apps.deportes.models import Campeonato, Equipo, Facultad, Inscripcion
from apps.fixture.models import Partido, TablaPosiciones
from apps.fixture.services.reparacion import NIVELES_PELIGROSOS, proponer_reparacion
from apps.ml.services.clima import DIAS_PRONOSTICO, ServicioClima
from apps.ml.services.predictor import PredictorResultados
from apps.users.models import Usuario
from apps.users.roles import es_admin, es_organizador

logger = logging.getLogger(__name__)

LECTURA, CALCULO, ESCRITURA = "LECTURA", "CALCULO", "ESCRITURA"
MAX_RESULTADO = 3500            # caracteres que se devuelven al modelo por herramienta
ROLES_DESTINO = [Usuario.Rol.ADMIN_DUBSS, Usuario.Rol.ORGANIZADOR, Usuario.Rol.DELEGADO]
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


class ErrorHerramienta(Exception):
    """Error esperado que el modelo puede leer y corregir (parámetro inválido, ambigüedad, sin datos)."""


class SinPermiso(ErrorHerramienta):
    pass


@dataclass
class Contexto:
    usuario: Usuario
    conversacion: ConversacionAgente
    acciones: list = field(default_factory=list)      # acciones pendientes creadas en esta petición
    descargas: list = field(default_factory=list)     # reportes listos para descargar


# ── Utilidades ────────────────────────────────────────────────────────────────

def limpiar(texto, largo: int = 160) -> str:
    """Texto de la base de datos: sin caracteres de control ni saltos, y acotado."""
    texto = re.sub(r"[\x00-\x1f\x7f]+", " ", str(texto or ""))
    return " ".join(texto.split())[:largo]


def _norm(texto) -> str:
    base = unicodedata.normalize("NFD", str(texto or "").lower())
    return "".join(c for c in base if unicodedata.category(c) != "Mn").strip()


def _fmt(momento: datetime) -> str:
    local = timezone.localtime(momento)
    return f"{DIAS[local.weekday()]} {local:%d/%m %H:%M}"


def _nombre_partido(p: Partido) -> str:
    local = p.equipo_local.nombre if p.equipo_local_id else "Por definir"
    visitante = p.equipo_visitante.nombre if p.equipo_visitante_id else "Por definir"
    return limpiar(f"{local} vs {visitante}", 120)


def _resolver(modelo, valor, campos, etiqueta: str, qs=None):
    """Entidad por id o por nombre (sin tildes ni mayúsculas). Si es ambigua, el modelo debe preguntar al usuario."""
    valor = str(valor).strip()
    qs = qs if qs is not None else modelo.objects.all()
    if valor.isdigit():
        encontrado = qs.filter(pk=int(valor)).first()
        if encontrado:
            return encontrado
    buscado = _norm(valor)
    candidatos = [o for o in qs[:500] if any(buscado in _norm(getattr(o, c)) for c in campos)]
    exactos = [o for o in candidatos if any(buscado == _norm(getattr(o, c)) for c in campos)]
    if len(exactos) == 1:
        return exactos[0]
    if len(candidatos) == 1:
        return candidatos[0]
    if not candidatos:
        raise ErrorHerramienta(f"No encontré {etiqueta} «{limpiar(valor, 60)}».")
    opciones = "; ".join(f"{o.pk}: {limpiar(getattr(o, campos[0]), 60)}" for o in candidatos[:8])
    raise ErrorHerramienta(f"«{limpiar(valor, 60)}» coincide con varios ({opciones}). Pregunta al usuario cuál quiere.")


def _campeonato(valor) -> Campeonato:
    return _resolver(Campeonato, valor, ("nombre",), "un campeonato")


def _dia_local(dia: date) -> tuple[datetime, datetime]:
    inicio = timezone.make_aware(datetime.combine(dia, time.min))
    return inicio, inicio + timedelta(days=1)


def _exigir_fecha_futura(dia: date) -> date:
    if dia < timezone.localdate():
        raise ErrorHerramienta("Esa fecha ya pasó. Usa una fecha de hoy en adelante.")
    return dia


# ── Parámetros ────────────────────────────────────────────────────────────────

class EntradaVacia(serializers.Serializer):
    pass


class EntradaListarCampeonatos(serializers.Serializer):
    estado = serializers.ChoiceField(choices=Campeonato.Estado.choices, required=False,
                                     help_text="Filtra por estado. Sin valor devuelve los vigentes (no finalizados ni cancelados).")


class EntradaTabla(serializers.Serializer):
    campeonato = serializers.CharField(max_length=200, help_text="Id o nombre (parcial) del campeonato.")


class EntradaListarPartidos(serializers.Serializer):
    campeonato = serializers.CharField(max_length=200, required=False, help_text="Id o nombre del campeonato.")
    equipo = serializers.CharField(max_length=200, required=False, help_text="Id o nombre del equipo.")
    desde = serializers.DateField(required=False, help_text="Fecha inicial YYYY-MM-DD.")
    hasta = serializers.DateField(required=False, help_text="Fecha final YYYY-MM-DD.")
    estado = serializers.ChoiceField(choices=Partido.Estado.choices, required=False)
    limite = serializers.IntegerField(min_value=1, max_value=30, default=15, required=False)


class EntradaClima(serializers.Serializer):
    fecha = serializers.DateField(help_text="Día a consultar, YYYY-MM-DD (máximo 16 días hacia adelante).")
    campeonato = serializers.CharField(max_length=200, required=False, help_text="Limita a un campeonato.")


class EntradaPredecir(serializers.Serializer):
    partido_id = serializers.IntegerField(min_value=1)


class EntradaReporte(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=["campeonato", "equipo", "facultad"])
    objetivo = serializers.CharField(max_length=200, help_text="Id o nombre del campeonato, equipo o facultad.")
    formato = serializers.ChoiceField(choices=["pdf", "excel"], default="pdf", required=False)


class EntradaProponer(serializers.Serializer):
    fecha = serializers.DateField(help_text="Día cuyos partidos se quieren reubicar, YYYY-MM-DD.")
    motivo = serializers.CharField(max_length=200, help_text="Por qué se reprograma (se muestra en los avisos).")
    campeonato = serializers.CharField(max_length=200, required=False, help_text="Limita a un campeonato.")
    criterio = serializers.ChoiceField(
        choices=["clima", "todos"], default="clima", required=False,
        help_text="clima: solo partidos al aire libre con riesgo ALTO o CRÍTICO. todos: todos los partidos programados "
                  "del día (solo si el usuario lo pide, p. ej. por un bloqueo de cancha).")
    dias_busqueda = serializers.IntegerField(min_value=1, max_value=14, default=7, required=False,
                                             help_text="Cuántos días después de la fecha se buscan horarios libres.")


class EntradaAplicar(serializers.Serializer):
    propuesta_id = serializers.IntegerField(min_value=1, help_text="Id devuelto por proponer_reprogramacion.")


class EntradaNotificar(serializers.Serializer):
    titulo = serializers.CharField(max_length=100)
    mensaje = serializers.CharField(max_length=500)
    roles = serializers.ListField(child=serializers.ChoiceField(choices=ROLES_DESTINO), required=False,
                                  help_text="Roles destinatarios: ADMIN_DUBSS, ORGANIZADOR, DELEGADO.")
    facultad = serializers.CharField(max_length=150, required=False, help_text="Id, nombre o sigla de la facultad.")
    campeonato = serializers.CharField(max_length=200, required=False, help_text="Delegados de los equipos de este campeonato.")
    todos = serializers.BooleanField(default=False, required=False, help_text="TODOS los usuarios activos: administradores, organizadores y delegados. Para avisar solo a delegados NO la uses: usa roles=[DELEGADO].")


def esquema(serializer_cls) -> dict:
    """JSON Schema de los parámetros, generado desde el mismo serializer que los valida."""
    tipos = {serializers.IntegerField: "integer", serializers.BooleanField: "boolean"}
    propiedades, requeridos = {}, []
    for nombre, campo in serializer_cls().fields.items():
        if isinstance(campo, serializers.ChoiceField):
            prop = {"type": "string", "enum": [str(c) for c in campo.choices]}
        elif isinstance(campo, serializers.ListField):
            hijo = campo.child
            prop = {"type": "array", "items": {"type": "string", **({"enum": [str(c) for c in hijo.choices]} if isinstance(hijo, serializers.ChoiceField) else {})}}
        elif isinstance(campo, serializers.DateField):
            prop = {"type": "string", "format": "date"}
        else:
            prop = {"type": next((t for k, t in tipos.items() if isinstance(campo, k)), "string")}
        if campo.help_text:
            prop["description"] = str(campo.help_text)
        propiedades[nombre] = prop
        if campo.required:
            requeridos.append(nombre)
    return {"type": "object", "properties": propiedades, "required": requeridos}


# ── Herramientas de lectura ───────────────────────────────────────────────────

def listar_campeonatos(ctx, d):
    qs = Campeonato.objects.select_related("categoria__deporte").order_by("-fecha_inicio")
    qs = qs.filter(estado=d["estado"]) if d.get("estado") else qs.exclude(estado__in=[Campeonato.Estado.FINALIZADO, Campeonato.Estado.CANCELADO])
    filas = [{
        "id": c.pk, "nombre": limpiar(c.nombre), "estado": c.estado, "formato": c.formato,
        "deporte": limpiar(c.categoria.deporte.nombre, 60),
        "equipos": c.inscripciones.filter(estado=Inscripcion.Estado.APROBADA).count(),
    } for c in qs[:20]]
    return {"campeonatos": filas}


def consultar_tabla(ctx, d):
    c = _campeonato(d["campeonato"])
    filas = TablaPosiciones.objects.filter(campeonato=c).select_related("equipo").order_by("posicion", "-puntos")
    return {"campeonato": limpiar(c.nombre), "estado": c.estado, "tabla": [
        {"pos": f.posicion, "equipo": limpiar(f.equipo.nombre, 80), "pj": f.pj, "pg": f.pg, "pe": f.pe, "pp": f.pp,
         "gf": f.gf, "gc": f.gc, "pts": f.puntos} for f in filas[:30]]}


def listar_partidos(ctx, d):
    qs = Partido.objects.select_related("campeonato", "equipo_local", "equipo_visitante", "cancha", "resultado")
    if d.get("campeonato"):
        qs = qs.filter(campeonato=_campeonato(d["campeonato"]))
    if d.get("equipo"):
        e = _resolver(Equipo, d["equipo"], ("nombre",), "un equipo")
        qs = qs.filter(Q(equipo_local=e) | Q(equipo_visitante=e))
    if d.get("desde"):
        qs = qs.filter(fecha_hora__gte=_dia_local(d["desde"])[0])
    if d.get("hasta"):
        qs = qs.filter(fecha_hora__lt=_dia_local(d["hasta"])[1])
    if d.get("estado"):
        qs = qs.filter(estado=d["estado"])
    elif not (d.get("desde") or d.get("hasta")):
        qs = qs.filter(estado=Partido.Estado.PROGRAMADO, fecha_hora__gte=timezone.now())   # por defecto: lo que viene
    total = qs.count()
    filas = []
    for p in qs.order_by("fecha_hora")[: d.get("limite", 15)]:
        res = getattr(p, "resultado", None)
        filas.append({
            "id": p.pk, "campeonato": limpiar(p.campeonato.nombre, 80), "jornada": p.jornada, "partido": _nombre_partido(p),
            "cuando": _fmt(p.fecha_hora), "cancha": limpiar(p.cancha.nombre, 60) if p.cancha_id else None,
            "techada": bool(p.cancha_id and p.cancha.techada), "estado": p.estado,
            **({"marcador": f"{res.goles_local}-{res.goles_visitante}"} if res else {}),
        })
    return {"total": total, "mostrados": len(filas), "partidos": filas}


def _riesgos_del_dia(partidos):
    """(serie_disponible, [(partido, riesgo|None)]) con UNA sola consulta de pronóstico."""
    servicio = ServicioClima()
    try:
        serie = servicio.serie()
    except Exception as e:  # noqa: BLE001
        logger.warning("El agente no pudo consultar Open-Meteo.", exc_info=True)
        raise ErrorHerramienta("No se pudo consultar el pronóstico del clima en este momento (Open-Meteo no responde).") from e
    return [(p, servicio.riesgo_de_ventana(serie, p.fecha_hora, p.fecha_hora_fin, bool(p.cancha_id and p.cancha.techada))) for p in partidos]


def ver_clima(ctx, d):
    dia = _exigir_fecha_futura(d["fecha"])
    if dia > timezone.localdate() + timedelta(days=DIAS_PRONOSTICO - 1):
        raise ErrorHerramienta(f"El pronóstico solo cubre {DIAS_PRONOSTICO} días hacia adelante.")
    inicio, fin = _dia_local(dia)
    qs = Partido.objects.filter(fecha_hora__gte=inicio, fecha_hora__lt=fin, estado=Partido.Estado.PROGRAMADO) \
        .select_related("campeonato", "equipo_local", "equipo_visitante", "cancha").order_by("fecha_hora")
    if d.get("campeonato"):
        qs = qs.filter(campeonato=_campeonato(d["campeonato"]))
    partidos = list(qs[:25])
    if not partidos:
        return {"fecha": dia.isoformat(), "partidos": [], "mensaje": "No hay partidos programados ese día."}
    filas = []
    for p, r in _riesgos_del_dia(partidos):
        filas.append({"partido_id": p.pk, "partido": _nombre_partido(p), "cuando": _fmt(p.fecha_hora),
                      "techada": bool(p.cancha_id and p.cancha.techada),
                      **({"riesgo": r[0], "detalle": r[2], "recomendacion": r[1]} if r else {"riesgo": "SIN_DATOS"})})
    return {"fecha": dia.isoformat(), "partidos": filas}


def predecir_partido(ctx, d):
    p = Partido.objects.select_related("campeonato__categoria", "equipo_local", "equipo_visitante").filter(pk=d["partido_id"]).first()
    if p is None:
        raise ErrorHerramienta("No existe un partido con ese id.")
    if not (p.equipo_local_id and p.equipo_visitante_id):
        raise ErrorHerramienta("El partido aún no tiene los dos equipos definidos.")
    r = PredictorResultados().predecir(p, persistir=False)
    return {"partido": _nombre_partido(p), "prob_local": r.prob_victoria_local, "prob_empate": r.prob_empate,
            "prob_visitante": r.prob_victoria_visit, "goles_esperados": [r.goles_local_pred, r.goles_visit_pred],
            "confianza": r.confianza, "datos_suficientes": r.datos_suficientes, "metodo": r.modelo_version,
            "aviso": None if r.datos_suficientes else "Pocos partidos jugados: es una estimación básica."}


def generar_reporte(ctx, d):
    tipo, formato = d["tipo"], d.get("formato", "pdf")
    if tipo == "campeonato":
        objeto, nombre = (o := _campeonato(d["objetivo"])), o.nombre
    elif tipo == "equipo":
        objeto, nombre = (o := _resolver(Equipo, d["objetivo"], ("nombre",), "un equipo")), o.nombre
    else:
        objeto, nombre = (o := _resolver(Facultad, d["objetivo"], ("nombre", "sigla"), "una facultad")), o.nombre
    descarga = {"recurso": tipo, "id": objeto.pk, "formato": formato, "nombre": limpiar(nombre, 120)}
    ctx.descargas.append(descarga)
    return {"mensaje": "El reporte está listo; el usuario lo descarga con el botón que aparece bajo tu respuesta.", **descarga}


# ── Cálculo: propuesta de reprogramación ─────────────────────────────────────

def _iso(momento) -> str:
    return timezone.localtime(momento).isoformat()


def proponer_reprogramacion(ctx, d):
    dia = _exigir_fecha_futura(d["fecha"])
    inicio, fin = _dia_local(dia)
    qs = Partido.objects.filter(
        fecha_hora__gte=inicio, fecha_hora__lt=fin, estado=Partido.Estado.PROGRAMADO,
        campeonato__estado=Campeonato.Estado.EN_CURSO, equipo_local__isnull=False, equipo_visitante__isnull=False,
    ).select_related("campeonato__categoria", "equipo_local", "equipo_visitante", "cancha").order_by("fecha_hora")
    if d.get("campeonato"):
        qs = qs.filter(campeonato=_campeonato(d["campeonato"]))
    del_dia = list(qs[:60])
    if not del_dia:
        return {"propuesta_id": None, "mensaje": "No hay partidos programados ese día (en campeonatos en curso)."}

    criterio = d.get("criterio", "clima")
    afectados, sin_riesgo = del_dia, []
    if criterio == "clima":
        riesgos = _riesgos_del_dia(del_dia)
        afectados = [p for p, r in riesgos if r and r[0] in NIVELES_PELIGROSOS and not (p.cancha_id and p.cancha.techada)]
        sin_riesgo = [f"{_nombre_partido(p)} ({_fmt(p.fecha_hora)}): " + (r[0] if r else "sin pronóstico") for p, r in riesgos if p not in afectados]
        if not afectados:
            return {"propuesta_id": None, "mensaje": "Ningún partido al aire libre de ese día tiene riesgo climático ALTO o CRÍTICO; no hace falta reprogramar.",
                    "partidos_revisados": sin_riesgo[:15]}

    propuesta = proponer_reparacion(afectados, desde=dia, hasta=dia + timedelta(days=d.get("dias_busqueda", 7)))
    cambios = [{
        "partido_id": c.partido.pk, "partido": _nombre_partido(c.partido), "campeonato": limpiar(c.partido.campeonato.nombre, 80),
        "jornada": c.partido.jornada,
        "delegados": sorted({e.delegado_id for e in (c.partido.equipo_local, c.partido.equipo_visitante) if e.delegado_id}),
        "anterior": {"cancha_id": c.partido.cancha_id, "cancha": limpiar(c.partido.cancha.nombre, 60) if c.partido.cancha_id else None,
                     "inicio": _iso(c.partido.fecha_hora)},
        "nuevo": {"cancha_id": c.cancha.pk, "cancha": limpiar(c.cancha.nombre, 60), "inicio": _iso(c.inicio), "fin": _iso(c.fin), "clima": c.clima},
        "desplazamiento_min": c.desplazamiento_min,
    } for c in propuesta.cambios]
    sin_solucion = [{"partido_id": p.pk, "partido": _nombre_partido(p), "motivo": m} for p, m in propuesta.sin_solucion]
    descartados = [{"partido_id": p.pk, "partido": _nombre_partido(p), "motivo": m} for p, m in propuesta.descartados]
    if not cambios:
        return {"propuesta_id": None, "mensaje": "No encontré horarios libres para reubicar los partidos afectados.", "sin_solucion": sin_solucion}

    datos = {
        "tipo": "reprogramacion", "motivo": limpiar(d["motivo"], 200), "fecha": dia.isoformat(), "criterio": criterio,
        "ventana": [propuesta.ventana[0].isoformat(), propuesta.ventana[1].isoformat()], "clima_verificado": propuesta.clima_verificado,
        "modelo": propuesta.modelo_version, "cambios": cambios, "sin_solucion": sin_solucion, "descartados": descartados,
    }
    guardada = PropuestaAgente.objects.create(usuario=ctx.usuario, conversacion=ctx.conversacion, herramienta="proponer_reprogramacion", datos=datos)
    return {
        "propuesta_id": guardada.pk,
        "partidos_afectados": len(afectados), "reubicados": len(cambios), "sin_solucion": sin_solucion,
        "cambios": [f"{c['partido']} ({c['campeonato']}): {_fmt(datetime.fromisoformat(c['anterior']['inicio']))} → "
                    f"{_fmt(datetime.fromisoformat(c['nuevo']['inicio']))} en {c['nuevo']['cancha']}"
                    + (f" [clima {c['nuevo']['clima']}]" if c["nuevo"]["clima"] else " [sin pronóstico]") for c in cambios],
        "clima_verificado": propuesta.clima_verificado,
    }


# ── Escritura: solo crean acciones pendientes ────────────────────────────────

def _crear_accion(ctx, herramienta: str, resumen: str, propuesta: dict) -> AccionPendiente:
    accion = AccionPendiente.objects.create(
        usuario=ctx.usuario, conversacion=ctx.conversacion, herramienta=herramienta, resumen=resumen[:300],
        propuesta=propuesta, expira_en=AccionPendiente.nueva_expiracion(),
    )
    ctx.acciones.append(accion)
    return accion


def aplicar_reprogramacion(ctx, d):
    prop = PropuestaAgente.objects.filter(pk=d["propuesta_id"], usuario=ctx.usuario, conversacion=ctx.conversacion,
                                          herramienta="proponer_reprogramacion").first()
    if prop is None:
        raise ErrorHerramienta("No existe esa propuesta en esta conversación. Calcúlala primero con proponer_reprogramacion.")
    if prop.creado_en < timezone.now() - timedelta(minutes=settings.AGENTE_ACCION_MINUTOS):
        raise ErrorHerramienta("La propuesta es demasiado antigua; el calendario pudo cambiar. Vuelve a calcularla.")
    previa = AccionPendiente.objects.filter(conversacion=ctx.conversacion, usuario=ctx.usuario, estado=AccionPendiente.Estado.PENDIENTE,
                                            propuesta__propuesta_id=prop.pk).first()
    if previa and not previa.vencida:
        ctx.acciones.append(previa)
        return {"estado": "PENDIENTE_DE_CONFIRMACION", "accion_id": previa.pk, "mensaje": "Esa propuesta ya está esperando la confirmación del usuario."}
    datos = prop.datos
    delegados = {u for c in datos["cambios"] for u in c["delegados"]}
    resumen = f"Reprogramar {len(datos['cambios'])} partido(s) y avisar a {len(delegados)} delegado(s). Motivo: {datos['motivo']}"
    accion = _crear_accion(ctx, "aplicar_reprogramacion", resumen, {**datos, "propuesta_id": prop.pk})
    return {"estado": "PENDIENTE_DE_CONFIRMACION", "accion_id": accion.pk,
            "mensaje": "Se creó la acción. NO se ha cambiado nada: el usuario debe revisar la tarjeta y pulsar «Confirmar». "
                       f"Vence en {settings.AGENTE_ACCION_MINUTOS} minutos."}


def _destinatarios(d) -> list[Usuario]:
    if not (d.get("todos") or d.get("roles") or d.get("facultad") or d.get("campeonato")):
        raise ErrorHerramienta("Indica a quién enviar: todos, roles, una facultad o un campeonato.")
    qs = Usuario.objects.filter(is_active=True, rol__in=ROLES_DESTINO)
    if not d.get("todos"):
        if d.get("roles"):
            qs = qs.filter(rol__in=d["roles"])
        if d.get("facultad"):
            qs = qs.filter(facultad=_resolver(Facultad, d["facultad"], ("nombre", "sigla"), "una facultad"))
        if d.get("campeonato"):
            c = _campeonato(d["campeonato"])
            qs = qs.filter(pk__in=Equipo.objects.filter(inscripciones__campeonato=c, inscripciones__estado=Inscripcion.Estado.APROBADA,
                                                        delegado__isnull=False).values("delegado_id"))
    return list(qs.order_by("pk")[:500])


def enviar_notificacion(ctx, d):
    destinatarios = _destinatarios(d)
    if not destinatarios:
        raise ErrorHerramienta("Ningún usuario activo coincide con esos destinatarios.")
    titulo, mensaje = limpiar(d["titulo"], 100), " ".join(str(d["mensaje"]).split())[:500]
    resumen = f"Enviar el aviso «{titulo}» a {len(destinatarios)} usuario(s)."
    accion = _crear_accion(ctx, "enviar_notificacion", resumen, {
        "tipo": "notificacion", "titulo": titulo, "mensaje": mensaje, "usuarios": [u.pk for u in destinatarios],
        "vista_previa": [limpiar(f"{u.nombre} {u.apellido} ({u.get_rol_display()})", 80) for u in destinatarios[:10]],
    })
    return {"estado": "PENDIENTE_DE_CONFIRMACION", "accion_id": accion.pk, "destinatarios": len(destinatarios),
            "mensaje": "Se creó la acción. NO se ha enviado nada: el usuario debe revisar el texto y pulsar «Confirmar»."}


# ── Registro ──────────────────────────────────────────────────────────────────

def _gestion(usuario) -> bool:
    return es_admin(usuario) or es_organizador(usuario)


@dataclass(frozen=True)
class Herramienta:
    nombre: str
    descripcion: str
    entrada: type
    tipo: str
    funcion: object
    etiqueta: str                  # cómo se muestra el paso a la persona
    permiso: object = _gestion

    def definicion(self) -> dict:
        return {"type": "function", "function": {"name": self.nombre, "description": self.descripcion, "parameters": esquema(self.entrada)}}


REGISTRO: dict[str, Herramienta] = {h.nombre: h for h in [
    Herramienta("listar_campeonatos", "Lista los campeonatos vigentes con su id, estado y cantidad de equipos. Úsala para descubrir ids.",
                EntradaListarCampeonatos, LECTURA, listar_campeonatos, "Consultó los campeonatos"),
    Herramienta("consultar_tabla", "Tabla de posiciones de un campeonato.", EntradaTabla, LECTURA, consultar_tabla, "Consultó la tabla de posiciones"),
    Herramienta("listar_partidos", "Lista partidos con filtros (campeonato, equipo, fechas, estado). Sin filtros devuelve los próximos programados.",
                EntradaListarPartidos, LECTURA, listar_partidos, "Consultó los partidos"),
    Herramienta("ver_clima", "Pronóstico y riesgo climático (BAJO, MEDIO, ALTO, CRITICO) de los partidos programados de un día. Las canchas techadas no sufren la lluvia.",
                EntradaClima, LECTURA, ver_clima, "Consultó el clima"),
    Herramienta("predecir_partido", "Probabilidades de victoria/empate de un partido con el modelo predictivo. Úsala para «quién gana»; necesita el id de un partido (búscalo con listar_partidos).",
                EntradaPredecir, LECTURA, predecir_partido, "Consultó la predicción"),
    Herramienta("generar_reporte", "Prepara un reporte PDF o Excel de un campeonato, equipo o facultad para que el usuario lo descargue.",
                EntradaReporte, LECTURA, generar_reporte, "Preparó un reporte"),
    Herramienta("proponer_reprogramacion", "Calcula nuevos horarios sin choques para los partidos de un día (por lluvia u otro motivo) usando el optimizador. "
                "SOLO PROPONE: no cambia nada. Devuelve un propuesta_id; si el usuario quiere reprogramar, llama a continuación a aplicar_reprogramacion con ese id (crea la tarjeta de confirmación).",
                EntradaProponer, CALCULO, proponer_reprogramacion, "Calculó una reprogramación"),
    Herramienta("aplicar_reprogramacion", "Solicita aplicar una propuesta de reprogramación. NO la ejecuta: crea una acción pendiente que el usuario "
                "debe confirmar con un botón. Úsala solo después de mostrar la propuesta al usuario.",
                EntradaAplicar, ESCRITURA, aplicar_reprogramacion, "Solicitó confirmar una reprogramación"),
    Herramienta("enviar_notificacion", "Solicita enviar un aviso (correo y push) a un grupo de usuarios. NO lo envía: crea una acción pendiente que el usuario debe confirmar.",
                EntradaNotificar, ESCRITURA, enviar_notificacion, "Solicitó confirmar un aviso"),
]}


def definiciones() -> list[dict]:
    return [h.definicion() for h in REGISTRO.values()]


@dataclass
class ResultadoPaso:
    ok: bool
    contenido: str          # lo que ve el modelo
    paso: dict              # lo que ve la persona: {"herramienta", "etiqueta", "ok", "detalle"}


def _paso(nombre, etiqueta, ok, detalle="", argumentos=None):
    return {"herramienta": nombre, "etiqueta": etiqueta, "ok": ok, "detalle": limpiar(detalle, 200),
            "argumentos": {k: limpiar(v, 80) for k, v in (argumentos or {}).items()}}


def ejecutar(nombre: str, argumentos: str, ctx: Contexto) -> ResultadoPaso:
    """Valida y ejecuta UNA llamada. Nunca lanza: los errores vuelven al modelo como datos para que pueda corregir."""
    herramienta = REGISTRO.get(nombre)
    crudo = None
    if herramienta is None:
        return ResultadoPaso(False, json.dumps({"error": f"La herramienta «{limpiar(nombre, 40)}» no existe."}, ensure_ascii=False),
                             _paso(nombre, "Herramienta inexistente", False))
    try:
        if not herramienta.permiso(ctx.usuario):
            raise SinPermiso("No tienes permiso para usar esta herramienta.")
        try:
            crudo = json.loads(argumentos or "{}")
        except ValueError as e:
            raise ErrorHerramienta("Los argumentos no son un JSON válido.") from e
        if not isinstance(crudo, dict):
            raise ErrorHerramienta("Los argumentos deben ser un objeto JSON.")
        s = herramienta.entrada(data=crudo)
        if not s.is_valid():
            problemas = "; ".join(f"{k}: {' '.join(str(x) for x in v)}" for k, v in s.errors.items())
            raise ErrorHerramienta(f"Parámetros inválidos — {problemas}")
        resultado = herramienta.funcion(ctx, s.validated_data)
        contenido = json.dumps({"datos": resultado}, ensure_ascii=False, default=str)
        if len(contenido) > MAX_RESULTADO:
            contenido = json.dumps({"datos_recortados": contenido[:MAX_RESULTADO]}, ensure_ascii=False)
        return ResultadoPaso(True, contenido, _paso(nombre, herramienta.etiqueta, True, argumentos=crudo))
    except ErrorHerramienta as e:
        return ResultadoPaso(False, json.dumps({"error": str(e)}, ensure_ascii=False), _paso(nombre, herramienta.etiqueta, False, str(e), crudo if isinstance(crudo, dict) else None))
    except Exception:  # noqa: BLE001 — un fallo interno no debe tumbar la conversación ni filtrar detalles al modelo
        logger.exception("Falló la herramienta del agente %s.", nombre)
        return ResultadoPaso(False, json.dumps({"error": "Falló internamente; informa al usuario que no pudiste completarlo."}, ensure_ascii=False),
                             _paso(nombre, herramienta.etiqueta, False, "Error interno"))
