"""F7-04 — Evalúa el agente con escenarios reales (necesita GROQ_API_KEY). Sobre un calendario sintético que se descarta."""
import json

from django.core.management.base import BaseCommand, CommandError

from apps.agente import evaluacion
from apps.agente.services import llm


class Command(BaseCommand):
    help = "Evalúa el agente del organizador con 20 escenarios (aciertos, pasos, seguridad y permisos)."

    def add_arguments(self, parser):
        parser.add_argument("--salida", help="Ruta de un archivo JSON donde guardar el informe.")
        parser.add_argument("--solo", nargs="+", help="Ids de escenarios a correr (p. ej. A1 N1). Sin esto corre todos.")

    def handle(self, *args, **opciones):
        if not llm.disponible():
            raise CommandError("Falta GROQ_API_KEY: la evaluación usa el LLM real.")
        informe = evaluacion.evaluar(set(opciones.get("solo") or []) or None)
        for r in informe["resultados"]:
            marca = "OK   " if r["ok"] else "FALLA"
            self.stdout.write(f"{marca} {r['id']:<3} {r['segundos']:>5}s {r['vueltas_llm']} vueltas  {r['herramientas']}  {r['fallos'] or ''}")
        if not informe.get("resumen"):
            raise CommandError("Ningún escenario coincide con --solo.")
        self.stdout.write(json.dumps({"permisos": informe["permisos"], "resumen": informe["resumen"], "modelo": informe["modelo"]}, ensure_ascii=False, indent=2))
        if opciones.get("salida"):
            with open(opciones["salida"], "w", encoding="utf-8") as f:
                json.dump(informe, f, ensure_ascii=False, indent=2)
