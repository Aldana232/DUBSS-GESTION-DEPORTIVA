from django.core.management.base import BaseCommand

from apps.ml.services.predictor import entrenar


class Command(BaseCommand):
    help = (
        "Entrena el predictor de resultados (RF15) con todo el historial, lo valida de forma temporal "
        "(walk-forward) contra líneas base y lo registra en ml.ModeloML."
    )

    def handle(self, *args, **opciones):
        r = entrenar()
        if not r["entrenado"]:
            self.stdout.write(self.style.WARNING(r["motivo"]))
            return
        m, f, e = r["modelo"], r["linea_base_frecuencia"], r["linea_base_elo"]
        self.stdout.write(f"Modelo {r['version']} con {r['partidos']} partidos ({r['partidos_validacion']} de validación).")
        for nombre, x in (("Modelo", m), ("Base frecuencia", f), ("Base Elo", e)):
            self.stdout.write(f"  {nombre:<16} accuracy {x['accuracy']:.3f}  log-loss {x['log_loss']:.3f}  "
                              f"Brier {x['brier']:.3f}  ECE {x['ece']:.3f}")
        estilo = self.style.SUCCESS if r["activo"] else self.style.WARNING
        self.stdout.write(estilo(r["conclusion"]))
