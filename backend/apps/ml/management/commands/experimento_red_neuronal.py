"""
F7-09 — Experimento (decisión D11): ¿una red neuronal pequeña supera al Random Forest prediciendo resultados?

Usa EXACTAMENTE el mismo conjunto de datos, las mismas variables calculadas «a la fecha» y la misma validación
*walk-forward* que el predictor de producción (`predictor.entrenar`), y las mismas métricas (log-loss, Brier, ECE,
acierto). Así la comparación es justa. No activa ningún modelo: solo informa.
"""
from __future__ import annotations

import warnings
from datetime import date

import numpy as np
from django.core.management.base import BaseCommand, CommandError
from sklearn.calibration import CalibratedClassifierCV
from sklearn.exceptions import ConvergenceWarning
from sklearn.model_selection import TimeSeriesSplit
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from apps.ml.services import predictor

MIN_PARTIDOS = 60


def _red(calibrar: bool):
    """Red pequeña y regularizada; se calibra igual que el Random Forest de producción para que la comparación sea justa."""
    base = make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(8,), alpha=1.0, max_iter=3000, random_state=7))
    return CalibratedClassifierCV(base, method="sigmoid", cv=3) if calibrar else base


class Command(BaseCommand):
    help = "Compara una red neuronal (MLP) con el Random Forest y las líneas base, con las mismas métricas."

    def add_arguments(self, parser):
        parser.add_argument("--salida", help="Ruta de un archivo .md donde guardar el informe.")

    def handle(self, *args, **opciones):
        X, y, _, huella = predictor.construir_dataset()
        n = len(y)
        if n < MIN_PARTIDOS:
            raise CommandError(f"Hay {n} partidos finalizados; se necesitan al menos {MIN_PARTIDOS} para una comparación honesta.")
        cortes = max(2, min(5, n // 12))
        tasa_global = float((y == 1).mean())
        P = {k: [] for k in ("Random Forest", "Red neuronal (MLP 8)", "Frecuencia histórica", "Elo")}
        y_test = []
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            for tr, te in TimeSeriesSplit(n_splits=cortes).split(X):
                if len(set(y[tr])) < 2:
                    continue
                rf, _ = predictor._ajustar(X[tr], y[tr], calibrar=len(tr) >= 60)
                P["Random Forest"].append(predictor._alinear(rf.predict_proba(X[te]), rf.classes_))
                red = _red(len(tr) >= 60).fit(X[tr], y[tr])
                P["Red neuronal (MLP 8)"].append(predictor._alinear(red.predict_proba(X[te]), red.classes_))
                P["Frecuencia histórica"].append(np.tile(np.bincount(y[tr], minlength=3) / len(tr), (len(te), 1)))
                tasa = float((y[tr] == 1).mean()) or tasa_global
                P["Elo"].append(np.array([predictor.probas_elo(f[0], f[1], max(0.03, min(0.4, tasa))) for f in X[te]]))
                y_test.append(y[te])
        if not y_test:
            raise CommandError("El historial tiene una sola clase de resultado: no se puede validar.")
        y_test = np.concatenate(y_test)
        m = {k: predictor._metricas(np.vstack(v), y_test) for k, v in P.items()}

        rf, nn = m["Random Forest"], m["Red neuronal (MLP 8)"]
        mejor_base = min(m["Frecuencia histórica"]["log_loss"], m["Elo"]["log_loss"])
        if nn["log_loss"] < rf["log_loss"] - 0.005:
            veredicto = "La red neuronal mejora al Random Forest en log-loss con estos datos."
        elif nn["log_loss"] > rf["log_loss"] + 0.005:
            veredicto = "La red neuronal NO mejora al Random Forest: es peor en log-loss."
        else:
            veredicto = "Empate técnico: la diferencia en log-loss entre la red neuronal y el Random Forest es menor a 0,005."
        supera_bases = "supera" if nn["log_loss"] < mejor_base - 0.005 else "no supera"

        filas = "\n".join(
            f"| {k} | {v['accuracy'] * 100:.1f} % | {v['log_loss']:.3f} | {v['brier']:.3f} | {v['ece']:.3f} |"
            for k, v in sorted(m.items(), key=lambda kv: kv[1]["log_loss"])
        )
        informe = f"""# Experimento F7-09 — Red neuronal frente a Random Forest

Generado el {date.today():%d/%m/%Y} con `python manage.py experimento_red_neuronal`.

## Datos y método
- **{n} partidos finalizados** (sin walkover), todos los deportes; huella de datos `{huella}`.
- Variables calculadas **a la fecha de cada partido** (Elo, forma, goles, descanso, historial directo): sin fuga de información.
- Validación **walk-forward** con {cortes} cortes en el tiempo; {len(y_test)} partidos de validación.
- Modelos: Random Forest (el de producción), red neuronal `MLPClassifier` con una capa oculta de 8 neuronas, regularización L2 (alpha=1), variables estandarizadas y calibración, y dos líneas base (frecuencia histórica y Elo).

## Resultados (menor es mejor en log-loss, Brier y ECE)
| Modelo | Acierto | Log-loss | Brier | ECE |
|---|---|---|---|---|
{filas}

## Conclusión
- {veredicto}
- La red neuronal {supera_bases} a la mejor línea base.
- Con pocos cientos de partidos y variables tabulares, los árboles suelen igualar o superar a una red pequeña y son más fáciles de explicar y mantener. Por eso la decisión D11 se mantiene: el sistema usa Random Forest en producción; la red neuronal queda como experimento documentado para quien requiera *deep learning* de forma explícita.
- Con más historial (varias temporadas) conviene repetir el experimento: `python manage.py experimento_red_neuronal --salida docs/EXPERIMENTO_RED_NEURONAL.md`.
"""
        self.stdout.write(informe)
        if opciones.get("salida"):
            with open(opciones["salida"], "w", encoding="utf-8") as f:
                f.write(informe)
