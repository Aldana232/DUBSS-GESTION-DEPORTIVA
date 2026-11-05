"""
apps/ml/services/niveles.py
F7-07 — Clustering de equipos (K-means) para sembrar llaves de eliminación y armar grupos equilibrados.

Idea: cada equipo se describe con su rendimiento REAL en el mismo deporte (todos los campeonatos finalizados):
puntos por partido, diferencia de goles por partido y forma reciente. K-means agrupa los equipos en niveles
(favoritos, intermedios...). La siembra ordena por nivel y, dentro del nivel, por fuerza; los grupos se arman con el
reparto «serpiente» sobre ese orden para que queden parejos.

Honestidad:
* Sin historial suficiente (menos de 4 equipos con 3 o más partidos) NO se inventa un orden: se conserva el orden de
  inscripción y se dice por qué (`datos_suficientes=False`).
* Un equipo sin historial no entra al agrupamiento: se siembra al final (enfrenta a los mejores) y se marca.
* Los walkover no cuentan como rendimiento. Todo es determinista (semilla fija).
"""
from __future__ import annotations

import logging
from collections import defaultdict

import numpy as np
from django.db.models import Q
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from apps.deportes.models import Campeonato, Inscripcion
from apps.fixture.models import Partido

logger = logging.getLogger(__name__)

MIN_PARTIDOS_EQUIPO = 3          # partidos previos para que el rendimiento de un equipo sea confiable
MIN_EQUIPOS_CON_HISTORIAL = 4    # equipos con historial para que agrupar tenga sentido
VENTANA_FORMA = 5
ETIQUETAS = {2: ["Favoritos", "Competitivos"], 3: ["Favoritos", "Intermedios", "En desarrollo"],
             4: ["Favoritos", "Competitivos", "Intermedios", "En desarrollo"]}


def _rendimiento(deporte_id: int, equipos_ids: list[int]) -> dict[int, dict]:
    """Rendimiento acumulado de cada equipo en el deporte (partidos finalizados, sin walkover), en orden cronológico."""
    filas: dict[int, list[tuple[int, int]]] = defaultdict(list)   # equipo -> [(a_favor, en_contra)]
    partidos = (
        Partido.objects.filter(
            estado=Partido.Estado.FINALIZADO, resultado__walkover=False, campeonato__categoria__deporte_id=deporte_id,
        ).filter(Q(equipo_local_id__in=equipos_ids) | Q(equipo_visitante_id__in=equipos_ids))
        .select_related("resultado").order_by("fecha_hora", "pk")
    )
    for p in partidos:
        r = p.resultado
        if p.equipo_local_id in equipos_ids:
            filas[p.equipo_local_id].append((r.goles_local, r.goles_visitante))
        if p.equipo_visitante_id in equipos_ids:
            filas[p.equipo_visitante_id].append((r.goles_visitante, r.goles_local))

    resultado = {}
    for equipo_id, partidos_eq in filas.items():
        puntos = [3 if f > c else 1 if f == c else 0 for f, c in partidos_eq]
        pj = len(partidos_eq)
        resultado[equipo_id] = {
            "partidos": pj, "ppp": sum(puntos) / pj, "dg_pp": sum(f - c for f, c in partidos_eq) / pj,
            "gf_pp": sum(f for f, _ in partidos_eq) / pj, "gc_pp": sum(c for _, c in partidos_eq) / pj,
            "forma": sum(puntos[-VENTANA_FORMA:]) / len(puntos[-VENTANA_FORMA:]),
        }
    return resultado


def _fuerza(matriz: np.ndarray) -> np.ndarray:
    """Índice compuesto (z-score): 50 % puntos por partido, 35 % diferencia de goles, 15 % forma reciente."""
    z = StandardScaler().fit_transform(matriz)
    return 0.50 * z[:, 0] + 0.35 * z[:, 1] + 0.15 * z[:, 2]


def _elegir_k(X: np.ndarray) -> tuple[KMeans, float | None]:
    """K-means con el número de niveles que da mejor silueta (entre 2 y 4, siempre con al menos 2 equipos por nivel en promedio)."""
    mejor, mejor_silueta = None, -1.0
    for k in range(2, min(4, len(X) - 1) + 1):
        modelo = KMeans(n_clusters=k, n_init=10, random_state=7).fit(X)
        if len(set(modelo.labels_)) < k:
            continue
        silueta = float(silhouette_score(X, modelo.labels_))
        if silueta > mejor_silueta + 1e-9:
            mejor, mejor_silueta = modelo, silueta
    if mejor is None:
        mejor = KMeans(n_clusters=2, n_init=10, random_state=7).fit(X)
        return mejor, None
    return mejor, mejor_silueta


def _grupos_serpiente(orden: list[dict], cantidad: int) -> list[dict]:
    """Reparte el orden de siembra en «serpiente» (1,2,3,3,2,1,...) para que los grupos queden parejos."""
    grupos = [[] for _ in range(cantidad)]
    for i, equipo in enumerate(orden):
        vuelta, pos = divmod(i, cantidad)
        grupos[pos if vuelta % 2 == 0 else cantidad - 1 - pos].append(equipo)
    salida = []
    for i, g in enumerate(grupos):
        fuerzas = [e["fuerza"] for e in g if e["fuerza"] is not None]
        salida.append({"nombre": f"Grupo {chr(65 + i)}", "equipos": [e["equipo_id"] for e in g],
                       "fuerza_media": round(float(np.mean(fuerzas)), 1) if fuerzas else None})
    return salida


def analizar(campeonato: Campeonato, *, grupos: int | None = None) -> dict:
    inscripciones = list(
        Inscripcion.objects.filter(campeonato=campeonato, estado=Inscripcion.Estado.APROBADA, equipo__estado="ACTIVO")
        .select_related("equipo__facultad").order_by("fecha_inscripcion", "pk")
    )
    equipos = [i.equipo for i in inscripciones]
    n = len(equipos)
    deporte_id = campeonato.categoria.deporte_id
    rend = _rendimiento(deporte_id, [e.pk for e in equipos])

    con_historial = [e for e in equipos if rend.get(e.pk, {}).get("partidos", 0) >= MIN_PARTIDOS_EQUIPO]
    suficientes = len(con_historial) >= MIN_EQUIPOS_CON_HISTORIAL
    info = {e.pk: {"equipo_id": e.pk, "nombre": e.nombre, "facultad": e.facultad.nombre, "sigla": e.facultad.sigla, "nivel": None,
                   "fuerza": None, "partidos": rend.get(e.pk, {}).get("partidos", 0),
                   "ppp": round(rend[e.pk]["ppp"], 2) if e.pk in rend else None,
                   "dg_pp": round(rend[e.pk]["dg_pp"], 2) if e.pk in rend else None,
                   "forma": round(rend[e.pk]["forma"], 2) if e.pk in rend else None,
                   "sin_historial": e not in con_historial} for e in equipos}

    resultado = {
        "campeonato": {"id": campeonato.pk, "nombre": campeonato.nombre, "formato": campeonato.formato, "deporte": campeonato.categoria.deporte.nombre},
        "equipos_total": n, "metodo": "inscripcion", "datos_suficientes": suficientes, "k": 0, "silueta": None,
        "niveles": [], "motivo": "",
    }
    if n < 2:
        resultado["motivo"] = "Se necesitan al menos 2 equipos con inscripción aprobada."
        resultado.update(equipos=list(info.values()), orden_siembra=[e.pk for e in equipos], cabezas_de_serie=[], grupos=[], balance=None)
        return resultado

    if suficientes:
        matriz = np.array([[rend[e.pk]["ppp"], rend[e.pk]["dg_pp"], rend[e.pk]["forma"]] for e in con_historial])
        fuerza = _fuerza(matriz)
        # La fuerza se muestra de 0 a 100 entre los equipos con historial.
        escala = (fuerza - fuerza.min()) / ((fuerza.max() - fuerza.min()) or 1.0) * 100
        modelo, silueta = _elegir_k(StandardScaler().fit_transform(matriz))
        medias = {c: float(np.mean(fuerza[modelo.labels_ == c])) for c in set(modelo.labels_)}
        orden_clusters = sorted(medias, key=lambda c: -medias[c])          # nivel 1 = el cluster más fuerte
        nivel_de = {c: i + 1 for i, c in enumerate(orden_clusters)}
        for e, f, c in zip(con_historial, escala, modelo.labels_):
            info[e.pk].update(fuerza=round(float(f), 1), nivel=nivel_de[int(c)])
        k = len(orden_clusters)
        resultado.update(metodo="kmeans", k=k, silueta=None if silueta is None else round(silueta, 3), niveles=[
            {"nivel": i + 1, "etiqueta": ETIQUETAS[k][i],
             "equipos": [eid for eid, d in info.items() if d["nivel"] == i + 1],
             "fuerza_media": round(float(np.mean([d["fuerza"] for d in info.values() if d["nivel"] == i + 1])), 1)} for i in range(k)])
        con = sorted((info[e.pk] for e in con_historial), key=lambda d: (d["nivel"], -d["fuerza"]))
        sin = [info[e.pk] for e in equipos if e not in con_historial]               # orden de inscripción, al final
        ordenados = con + sin
        resultado["motivo"] = (f"{len(sin)} equipo(s) sin historial suficiente se siembran al final." if sin else
                               "Todos los equipos tienen historial suficiente.")
    else:
        ordenados = [info[e.pk] for e in equipos]
        resultado["motivo"] = (f"No hay historial suficiente: se necesitan al menos {MIN_EQUIPOS_CON_HISTORIAL} equipos con "
                               f"{MIN_PARTIDOS_EQUIPO} o más partidos jugados en este deporte. Se mantiene el orden de inscripción.")

    for semilla, d in enumerate(ordenados, start=1):
        d["semilla"] = semilla
    tamano = 1
    while tamano < n:
        tamano *= 2
    cantidad_grupos = grupos if grupos else (max(2, n // 4) if n >= 4 else 1)
    cantidad_grupos = max(1, min(cantidad_grupos, max(1, n // 2)))
    lista_grupos = _grupos_serpiente(ordenados, cantidad_grupos)
    fuerzas = [g["fuerza_media"] for g in lista_grupos if g["fuerza_media"] is not None]
    resultado.update(
        equipos=ordenados, orden_siembra=[d["equipo_id"] for d in ordenados],
        cabezas_de_serie=[d["equipo_id"] for d in ordenados[:max(2, min(8, tamano // 4))]] if n >= 4 else [],
        grupos=lista_grupos,
        balance={"diferencia_max": round(max(fuerzas) - min(fuerzas), 1)} if len(fuerzas) > 1 else None,
    )
    return resultado
