"""
apps/asistente/services/intents.py
F6-06 — Interpretación de órdenes en español (texto → intención de una LISTA BLANCA + parámetros).

Dos intérpretes con el mismo resultado:
* LLM (Groq u Ollama): devuelve JSON con la intención y los NOMBRES mencionados.
* Reglas locales: funciona sin clave ni internet y es el respaldo cuando el LLM falla.

En ambos casos los nombres se resuelven aquí contra la base de datos (nunca los ids ni SQL los pone el LLM),
y si algo es ambiguo o falta, se pide una aclaración en vez de adivinar.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass, field


from apps.deportes.models import Campeonato, Equipo, FichaJugador

# ── Lista blanca ──────────────────────────────────────────────────────────────
INTENCIONES = {
    "reporte_campeonato": {"requiere": ["campeonato"], "descripcion": "Descargar el reporte (PDF o Excel) de un campeonato"},
    "tabla_posiciones": {"requiere": ["campeonato"], "descripcion": "Ver la tabla de posiciones de un campeonato"},
    "estadisticas_jugador": {"requiere": ["jugador"], "descripcion": "Estadísticas de un jugador"},
    "estadisticas_equipo": {"requiere": ["equipo"], "descripcion": "Estadísticas de un equipo"},
    "proximos_partidos": {"requiere": [], "descripcion": "Próximos partidos (de un campeonato o equipo)"},
    "resumen_torneo": {"requiere": ["campeonato"], "descripcion": "Resumen del estado de un campeonato"},
}
FORMATOS = ("pdf", "excel")
ETIQUETA = {"campeonato": "campeonato", "equipo": "equipo", "jugador": "jugador"}

PALABRAS_VACIAS = {
    "de", "del", "la", "el", "los", "las", "un", "una", "en", "y", "a", "al", "para", "por", "con", "que", "me", "mi", "su",
    "campeonato", "torneo", "copa", "equipo", "jugador", "liga", "facultad", "universitario", "interfacultativo", "campeonatos",
}


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9ñ ]", " ", texto)).strip()


def _tokens_utiles(texto: str) -> list[str]:
    return [t for t in normalizar(texto).split() if t not in PALABRAS_VACIAS and len(t) >= 3]


# ── Resultado ─────────────────────────────────────────────────────────────────

@dataclass
class Interpretacion:
    estado: str                                   # ok | aclaracion | no_entendido
    texto: str
    proveedor: str = "reglas"
    intencion: str | None = None
    formato: str | None = None
    parametros: dict = field(default_factory=dict)        # {"campeonato": {"id", "nombre"}, ...}
    supuestos: list[str] = field(default_factory=list)
    aclaracion: dict | None = None                         # {"campo", "pregunta", "opciones": [{"id","nombre"}]}
    mensaje: str = ""

    def como_dict(self) -> dict:
        return {k: getattr(self, k) for k in (
            "estado", "texto", "proveedor", "intencion", "formato", "parametros", "supuestos", "aclaracion", "mensaje")}


# ── Detección de intención por reglas ─────────────────────────────────────────

def _contiene(texto: str, palabras) -> bool:
    return any(re.search(rf"\b{re.escape(p)}\b", texto) for p in palabras)


def detectar_formato(texto_norm: str) -> str | None:
    if _contiene(texto_norm, ("excel", "xlsx", "planilla", "hoja de calculo")):
        return "excel"
    if _contiene(texto_norm, ("pdf", "documento")):
        return "pdf"
    return None


def detectar_intencion(texto_norm: str) -> str | None:
    """Intención por palabras clave, en orden de especificidad. None si no se reconoce ninguna."""
    if _contiene(texto_norm, ("proximos partidos", "proximo partido", "siguientes partidos", "siguiente partido",
                              "calendario", "cuando juega", "cuando juegan", "que partidos hay", "partidos de la semana",
                              "partidos de hoy", "partidos de manana", "agenda")):
        return "proximos_partidos"
    if _contiene(texto_norm, ("tabla", "posiciones", "clasificacion", "quien va primero", "quien lidera", "lider", "puntajes")):
        return "tabla_posiciones"
    if _contiene(texto_norm, ("resumen", "como va", "como esta", "como van", "situacion", "estado del")):
        return "resumen_torneo"
    if _contiene(texto_norm, ("estadisticas", "estadistica", "goles", "goleador", "tarjetas", "rendimiento", "cuantos goles",
                              "amarillas", "rojas", "como juega")):
        return "estadisticas"        # se resuelve a jugador o equipo según la entidad mencionada
    if _contiene(texto_norm, ("reporte", "informe", "descargar", "exportar", "bajar", "imprimir")):
        return "reporte_campeonato"
    return None


# ── Resolución de nombres contra la base ──────────────────────────────────────

def _puntaje(nombre: str, texto_norm: str, tokens_texto: set[str]) -> float:
    """0-1: qué tan claramente `nombre` está mencionado en el texto (tolera errores de transcripción)."""
    n = normalizar(nombre)
    if not n:
        return 0.0
    if re.search(rf"\b{re.escape(n)}\b", texto_norm):
        return 1.0
    utiles = _tokens_utiles(nombre)
    if not utiles:
        return 0.0
    aciertos = 0.0
    for t in utiles:
        if t in tokens_texto:
            aciertos += 1
        else:
            cercano = difflib.get_close_matches(t, tokens_texto, n=1, cutoff=0.84)
            aciertos += 0.9 if cercano else 0
    return aciertos / len(utiles) * (0.95 if len(utiles) > 1 else 0.9)


def _buscar(candidatos, texto_norm: str, minimo: float = 0.45) -> list[tuple[float, object]]:
    tokens = set(texto_norm.split())
    puntuados = [(_puntaje(nombre, texto_norm, tokens), obj) for nombre, obj in candidatos]
    return sorted(((p, o) for p, o in puntuados if p >= minimo), key=lambda x: -x[0])


def _candidatos(campo: str):
    if campo == "campeonato":
        return [(c.nombre, c) for c in Campeonato.objects.exclude(estado=Campeonato.Estado.CANCELADO)]
    if campo == "equipo":
        return [(e.nombre, e) for e in Equipo.objects.filter(estado="ACTIVO").select_related("facultad")]
    return [(f"{j.nombre} {j.apellido}", j) for j in FichaJugador.objects.filter(estado="ACTIVO").select_related("equipo")]


def _nombre(campo: str, obj) -> str:
    if campo == "jugador":
        return f"{obj.nombre} {obj.apellido} ({obj.equipo.nombre})"
    if campo == "equipo":
        return f"{obj.nombre} ({obj.facultad.sigla})"
    return obj.nombre


def _opcion(campo: str, obj) -> dict:
    return {"id": obj.pk, "nombre": _nombre(campo, obj)}


def resolver_entidad(campo: str, mencion: str | None, texto_norm: str):
    """
    Devuelve (objeto|None, opciones). `opciones` no vacío = ambiguo (hay que preguntar).
    Se busca primero por lo que extrajo el intérprete y, si no, en todo el texto.
    """
    for fuente in filter(None, (normalizar(mencion) if mencion else None, texto_norm)):
        encontrados = _buscar(_candidatos(campo), fuente)
        if not encontrados:
            continue
        mejor = encontrados[0][0]
        cercanos = [o for p, o in encontrados if p >= mejor - 0.12]
        # Se resuelve sola si se dijo el nombre completo, o si la mención es parcial pero nadie más compite.
        # Una mención parcial con otros candidatos parecidos («ingeniería» con dos equipos) se pregunta.
        if len(cercanos) == 1 and (mejor >= 0.99 or len(encontrados) == 1):
            return cercanos[0], []
        return None, [_opcion(campo, o) for _, o in encontrados[:6]]
    return None, []


# ── Orquestación ──────────────────────────────────────────────────────────────

def _campeonato_por_defecto():
    """Si hay un único campeonato vigente, es el que la persona seguramente quiere (se informa como supuesto)."""
    vigentes = list(Campeonato.objects.filter(estado__in=[Campeonato.Estado.EN_CURSO, Campeonato.Estado.INSCRIPCION_CERRADA,
                                                          Campeonato.Estado.INSCRIPCIONES]))
    en_curso = [c for c in vigentes if c.estado == Campeonato.Estado.EN_CURSO]
    if len(en_curso) == 1:
        return en_curso[0]
    if len(vigentes) == 1:
        return vigentes[0]
    return None


def _pregunta(campo: str, opciones: list[dict]) -> dict:
    if opciones:
        return {"campo": campo, "pregunta": f"Encontré varios {ETIQUETA[campo]}s parecidos. ¿Cuál quieres?", "opciones": opciones}
    return {"campo": campo, "pregunta": f"¿De qué {ETIQUETA[campo]} hablas? Repite la orden diciendo el nombre.",
            "opciones": [_opcion("campeonato", c) for c in Campeonato.objects.exclude(estado=Campeonato.Estado.CANCELADO)
                         .order_by("-fecha_inicio")[:6]] if campo == "campeonato" else []}


def completar(texto: str, proveedor: str, intencion: str | None, formato: str | None, menciones: dict,
              seleccion: dict | None = None) -> Interpretacion:
    """
    Convierte (intención, nombres mencionados) en una Interpretacion con parámetros resueltos,
    o en una aclaración si falta algo o es ambiguo. `seleccion` = elecciones ya hechas por el usuario.
    """
    texto_norm = normalizar(texto)
    seleccion = seleccion or {}
    if intencion == "estadisticas":
        # Jugador o equipo según a quién se mencione (si se mencionan los dos, manda el jugador).
        if seleccion.get("jugador") or resolver_entidad("jugador", menciones.get("jugador"), texto_norm)[0] \
                or _contiene(texto_norm, ("jugador", "goleador")):
            intencion = "estadisticas_jugador"
        else:
            intencion = "estadisticas_equipo"
    if intencion not in INTENCIONES:
        return Interpretacion("no_entendido", texto, proveedor, mensaje=(
            "No entendí qué necesitas. Prueba con: «reporte del campeonato en Excel», «tabla de posiciones», "
            "«próximos partidos» o «estadísticas del equipo …»."))

    resultado = Interpretacion("ok", texto, proveedor, intencion=intencion, formato=formato if intencion != "proximos_partidos" else None)
    campos = list(INTENCIONES[intencion]["requiere"])
    if intencion == "proximos_partidos":
        campos = ["campeonato", "equipo"]          # opcionales: filtran si se mencionan

    for campo in campos:
        obligatorio = campo in INTENCIONES[intencion]["requiere"]
        if seleccion.get(campo):
            modelos = {"campeonato": Campeonato, "equipo": Equipo, "jugador": FichaJugador}
            obj = modelos[campo].objects.filter(pk=seleccion[campo]).first()
            if obj is None:
                return Interpretacion("no_entendido", texto, proveedor, mensaje="La opción elegida ya no existe.")
            resultado.parametros[campo] = _opcion(campo, obj)
            continue
        # Para los filtros opcionales solo se busca si el intérprete extrajo un nombre o el texto lo contiene.
        obj, opciones = resolver_entidad(campo, menciones.get(campo), texto_norm)
        if obj is not None:
            resultado.parametros[campo] = _opcion(campo, obj)
        elif opciones:
            resultado.estado, resultado.aclaracion = "aclaracion", _pregunta(campo, opciones)
            return resultado
        elif obligatorio:
            if campo == "campeonato" and (por_defecto := _campeonato_por_defecto()):
                resultado.parametros[campo] = _opcion(campo, por_defecto)
                resultado.supuestos.append(f"No indicaste el campeonato: usé «{por_defecto.nombre}», el único vigente.")
            else:
                resultado.estado, resultado.aclaracion = "aclaracion", _pregunta(campo, [])
                return resultado
    if intencion in ("reporte_campeonato",) and resultado.formato is None:
        resultado.formato = "pdf"
        resultado.supuestos.append("No indicaste el formato: se descargará en PDF.")
    resultado.mensaje = f"Entendí: {INTENCIONES[intencion]['descripcion'].lower()}."
    return resultado


def interpretar_por_reglas(texto: str, previo: dict | None = None, seleccion: dict | None = None) -> Interpretacion:
    texto_norm = normalizar(texto)
    previo = previo or {}
    intencion = previo.get("intencion") or detectar_intencion(texto_norm)
    formato = previo.get("formato") or detectar_formato(texto_norm)
    return completar(texto, "reglas", intencion, formato, {}, seleccion)


