from django.core.management.base import BaseCommand

from apps.ml.services.asignacion_scorer import (
    entrenar_arranque_en_frio, info_modelo, reentrenar,
)


class Command(BaseCommand):
    help = (
        "Entrena el puntuador de asignaciones del fixture (RF11). Por defecto hace el arranque en frío "
        "(muestras etiquetadas con reglas explícitas); con --historial suma los partidos reales."
    )

    def add_arguments(self, parser):
        parser.add_argument("--historial", action="store_true", help="Reentrena con reglas + partidos reales.")
        parser.add_argument("--muestras", type=int, default=3000, help="Muestras de arranque en frío.")

    def handle(self, *args, **opciones):
        scorer = reentrenar() if opciones["historial"] else entrenar_arranque_en_frio(opciones["muestras"])
        m = scorer.metricas
        self.stdout.write(self.style.SUCCESS(
            f"Modelo {scorer.version} entrenado con {m['muestras']} muestras "
            f"({m['muestras_reales']} reales). Exactitud {m['exactitud']:.1%}, F1 {m['f1']:.1%}, AUC {m['auc']:.3f}."
        ))
        self.stdout.write(f"Etiquetado: {m['etiquetado']}")
        self.stdout.write(f"Estado: {info_modelo()['version']}")
