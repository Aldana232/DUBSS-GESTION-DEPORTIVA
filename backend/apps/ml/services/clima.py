"""
apps/ml/services/clima.py
CU15 / F6-07 — Riesgo climático de un partido con el pronóstico de Open-Meteo.

Open-Meteo es gratuito y no requiere clave. Las canchas no guardan coordenadas, así que se usan
las del campus (`CLIMA_LATITUD` / `CLIMA_LONGITUD`, por defecto Santa Cruz de la Sierra).

Criterios:
* El pronóstico solo existe hasta 16 días hacia adelante: más allá se dice «sin datos», nunca «riesgo bajo».
* Se evalúa la ventana completa del partido (todas las horas que cubre), no una sola hora.
* Una cancha techada no sufre la lluvia; sí el viento extremo y el frío.
* Si la consulta falla o el partido ya pasó, el nivel es SIN_DATOS (y NO se pisa un pronóstico previo válido).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.utils import timezone

from apps.fixture.models import Partido
from apps.ml.models import RiesgoClimatico

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
FUENTE = "Open-Meteo"
DIAS_PRONOSTICO = 16
N = RiesgoClimatico.NivelRiesgo


class ServicioClima:
    """Consulta el pronóstico para el horario de un partido y determina el nivel de riesgo."""

    UMBRALES = {
        "lluvia_mm":   {"medio": 2.5, "alto": 7.5, "critico": 15.0},   # acumulado durante el partido
        "viento_kmh":  {"medio": 30, "alto": 50, "critico": 70},
        "temp_c_baja": {"medio": 10, "alto": 5, "critico": 0},
        "temp_c_alta": {"medio": 33, "alto": 37, "critico": 40},
    }

    # ── API pública ───────────────────────────────────────────────────────────

    def consultar(self, partido: Partido, *, persistir: bool = True) -> RiesgoClimatico:
        ahora = timezone.now()
        fin = partido.fecha_hora_fin or partido.fecha_hora + timedelta(minutes=partido.duracion_min or 90)
        if fin < ahora:
            return self._sin_datos(partido, "El partido ya se jugó: no hay pronóstico.", persistir=False)
        if partido.fecha_hora > ahora + timedelta(days=DIAS_PRONOSTICO):
            return self._sin_datos(
                partido,
                f"El pronóstico solo cubre {DIAS_PRONOSTICO} días: se podrá consultar más cerca de la fecha.",
                persistir=False,
            )
        try:
            horas = self._pronostico(partido.fecha_hora, fin)
        except (requests.RequestException, KeyError, ValueError):
            logger.warning("No se pudo consultar Open-Meteo para el partido %s.", partido.pk, exc_info=True)
            return self._sin_datos(partido, "No se pudo consultar el pronóstico.", persistir=False)
        if not horas:
            return self._sin_datos(partido, "Open-Meteo no devolvió datos para ese horario.", persistir=False)

        techada = bool(partido.cancha and partido.cancha.techada)
        lluvia = round(sum(h["lluvia"] for h in horas), 1)
        viento = round(max(h["viento"] for h in horas), 1)
        temp = round(sum(h["temp"] for h in horas) / len(horas), 1)
        prob = max(h["prob_lluvia"] for h in horas)
        nivel, recomendacion = self.calcular_riesgo(temp, viento, lluvia, techada)
        descripcion = (f"{temp} °C, viento hasta {viento} km/h, {lluvia} mm de lluvia"
                       f" (probabilidad {prob} %)" + (", cancha techada" if techada else "") + ".")
        return self._guardar(partido, {
            "nivel_riesgo": nivel, "temperatura": temp, "precipitacion": lluvia, "viento": viento,
            "descripcion": descripcion, "recomendacion": recomendacion, "fuente_api": FUENTE,
        }, persistir=persistir)

    # ── Consulta a Open-Meteo ─────────────────────────────────────────────────

    def serie(self) -> list[dict]:
        """Pronóstico horario completo (16 días) en UNA consulta; sirve para evaluar muchos horarios sin repetir la red."""
        respuesta = requests.get(OPEN_METEO_URL, params={
            "latitude": settings.CLIMA_LATITUD, "longitude": settings.CLIMA_LONGITUD,
            "hourly": "temperature_2m,precipitation,precipitation_probability,wind_speed_10m",
            "forecast_days": DIAS_PRONOSTICO, "timezone": settings.TIME_ZONE,
        }, timeout=12)
        respuesta.raise_for_status()
        datos = respuesta.json()["hourly"]
        tz = timezone.get_current_timezone()
        return [{
            "momento": timezone.make_aware(datetime.fromisoformat(marca), tz),
            "temp": datos["temperature_2m"][i] or 0.0,
            "lluvia": datos["precipitation"][i] or 0.0,
            "prob_lluvia": datos["precipitation_probability"][i] or 0,
            "viento": datos["wind_speed_10m"][i] or 0.0,
        } for i, marca in enumerate(datos["time"])]

    @staticmethod
    def horas_de(serie: list[dict], desde, hasta) -> list[dict]:
        tz = timezone.get_current_timezone()
        inicio = desde.astimezone(tz).replace(minute=0, second=0, microsecond=0)
        return [h for h in serie if inicio <= h["momento"] < hasta.astimezone(tz)]

    def riesgo_de_ventana(self, serie: list[dict], desde, hasta, techada: bool):
        """(nivel, recomendación, resumen) de una ventana horaria, o None si el pronóstico no la cubre."""
        horas = self.horas_de(serie, desde, hasta)
        if not horas:
            return None
        lluvia = round(sum(h["lluvia"] for h in horas), 1)
        viento = round(max(h["viento"] for h in horas), 1)
        temp = round(sum(h["temp"] for h in horas) / len(horas), 1)
        nivel, recomendacion = self.calcular_riesgo(temp, viento, lluvia, techada)
        return nivel, recomendacion, f"{temp} °C, viento hasta {viento} km/h, {lluvia} mm de lluvia"

    def _pronostico(self, desde, hasta) -> list[dict]:
        return self.horas_de(self.serie(), desde, hasta)

    # ── Criterio de riesgo ────────────────────────────────────────────────────

    def calcular_riesgo(self, temp, viento, lluvia, techada):
        u = self.UMBRALES
        orden = [N.BAJO, N.MEDIO, N.ALTO, N.CRITICO]
        nivel, factores = N.BAJO, []

        def elevar(nuevo):
            nonlocal nivel
            if orden.index(nuevo) > orden.index(nivel):
                nivel = nuevo

        if not techada:
            for clave, etiqueta in (("critico", "Lluvia intensa"), ("alto", "Lluvia fuerte"), ("medio", "Lluvia leve")):
                if lluvia >= u["lluvia_mm"][clave]:
                    elevar({"critico": N.CRITICO, "alto": N.ALTO, "medio": N.MEDIO}[clave])
                    factores.append(f"{etiqueta} ({lluvia} mm)")
                    break
        for clave, etiqueta in (("critico", "Viento muy fuerte"), ("alto", "Viento fuerte"), ("medio", "Viento moderado")):
            if viento >= u["viento_kmh"][clave]:
                elevar({"critico": N.CRITICO, "alto": N.ALTO, "medio": N.MEDIO}[clave])
                factores.append(f"{etiqueta} ({viento:.0f} km/h)")
                break
        for clave, etiqueta in (("critico", "Temperatura extremadamente baja"), ("alto", "Temperatura muy baja"), ("medio", "Temperatura baja")):
            if temp <= u["temp_c_baja"][clave]:
                elevar({"critico": N.CRITICO, "alto": N.ALTO, "medio": N.MEDIO}[clave])
                factores.append(f"{etiqueta} ({temp:.0f} °C)")
                break
        for clave, etiqueta in (("critico", "Calor extremo"), ("alto", "Calor muy alto"), ("medio", "Calor alto")):
            if temp >= u["temp_c_alta"][clave]:
                elevar({"critico": N.CRITICO, "alto": N.ALTO, "medio": N.MEDIO}[clave])
                factores.append(f"{etiqueta} ({temp:.0f} °C)")
                break

        if not factores:
            return N.BAJO, "Condiciones favorables para el partido."
        detalle = "; ".join(factores) + "."
        if nivel == N.CRITICO:
            return nivel, f"Se recomienda SUSPENDER o REPROGRAMAR el partido. {detalle}"
        if nivel == N.ALTO:
            return nivel, f"Considerar reprogramación. {detalle}"
        return nivel, f"Monitorear las condiciones. {detalle}"

    # ── Persistencia ──────────────────────────────────────────────────────────

    def _sin_datos(self, partido, motivo, *, persistir):
        """SIN_DATOS nunca se confunde con riesgo bajo, y no reemplaza un pronóstico anterior válido."""
        return self._guardar(partido, {
            "nivel_riesgo": N.SIN_DATOS, "descripcion": motivo,
            "recomendacion": "Verificar las condiciones manualmente.", "fuente_api": "N/A",
        }, persistir=persistir)

    @staticmethod
    def _guardar(partido, valores, *, persistir):
        if not persistir:
            return RiesgoClimatico(partido=partido, **valores)
        riesgo, _ = RiesgoClimatico.objects.update_or_create(partido=partido, defaults=valores)
        return riesgo


def ultimo_riesgo(partido: Partido) -> RiesgoClimatico | None:
    """Último pronóstico guardado (lo calcula la tarea programada). No consulta la red ni escribe."""
    return partido.riesgos_climaticos.first()
