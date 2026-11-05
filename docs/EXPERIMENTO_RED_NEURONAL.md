# Experimento F7-09 — Red neuronal frente a Random Forest

Generado el 30/10/2026 con `python manage.py experimento_red_neuronal`.

## Datos y método
- **112 partidos finalizados** (sin walkover), todos los deportes; huella de datos `63a55778f6ac90c8ff03b80ee8c53f41d3ee8acd517ccad99f3d70cd8a16647f`.
- Variables calculadas **a la fecha de cada partido** (Elo, forma, goles, descanso, historial directo): sin fuga de información.
- Validación **walk-forward** con 5 cortes en el tiempo; 90 partidos de validación.
- Modelos: Random Forest (el de producción), red neuronal `MLPClassifier` con una capa oculta de 8 neuronas, regularización L2 (alpha=1), variables estandarizadas y calibración, y dos líneas base (frecuencia histórica y Elo).

## Resultados (menor es mejor en log-loss, Brier y ECE)
| Modelo | Acierto | Log-loss | Brier | ECE |
|---|---|---|---|---|
| Elo | 50.0 % | 1.044 | 0.622 | 0.073 |
| Frecuencia histórica | 47.8 % | 1.068 | 0.642 | 0.083 |
| Random Forest | 41.1 % | 1.122 | 0.680 | 0.106 |
| Red neuronal (MLP 8) | 41.1 % | 1.791 | 0.861 | 0.241 |

## Conclusión
- La red neuronal NO mejora al Random Forest: es peor en log-loss.
- La red neuronal no supera a la mejor línea base.
- Con pocos cientos de partidos y variables tabulares, los árboles suelen igualar o superar a una red pequeña y son más fáciles de explicar y mantener. Por eso la decisión D11 se mantiene: el sistema usa Random Forest en producción; la red neuronal queda como experimento documentado para quien requiera *deep learning* de forma explícita.
- Con más historial (varias temporadas) conviene repetir el experimento: `python manage.py experimento_red_neuronal --salida docs/EXPERIMENTO_RED_NEURONAL.md`.
