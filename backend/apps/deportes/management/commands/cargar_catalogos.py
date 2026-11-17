"""
Carga los catálogos BASE de la DUBSS en una instalación nueva: las 12 facultades de la UAGRM, los deportes y sus
categorías (Varones / Damas). NO crea usuarios, equipos, jugadores, campeonatos ni partidos (eso es de `seed_realista`,
que solo corre en desarrollo). Es idempotente: se puede repetir sin duplicar.

    python manage.py cargar_catalogos
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.deportes.management.commands import _datos_uagrm as D
from apps.deportes.models import Categoria, Deporte, Facultad


class Command(BaseCommand):
    help = "Carga facultades, deportes y categorías base (idempotente, sin datos de ejemplo)."

    @transaction.atomic
    def handle(self, *args, **opciones):
        nuevas = {"facultades": 0, "deportes": 0, "categorias": 0}
        for sigla, nombre, *_ in D.FACULTADES:
            _, creada = Facultad.objects.get_or_create(sigla=sigla, defaults={"nombre": nombre})
            nuevas["facultades"] += creada
        for nombre, jugadores, descripcion in D.DEPORTES:
            deporte, creado = Deporte.objects.get_or_create(
                nombre=nombre, defaults={"cantidad_jugadores": jugadores, "descripcion": descripcion})
            nuevas["deportes"] += creado
            for genero, etiqueta in (("VARONES", "Varones"), ("DAMAS", "Damas")):
                _, creada = Categoria.objects.get_or_create(
                    deporte=deporte, nombre=f"{nombre} {etiqueta}",
                    defaults={"genero": genero, "rango_edad": "Libre universitario",
                              "descripcion": f"Categoría {etiqueta.lower()} de {nombre.lower()} para estudiantes regulares de la UAGRM."})
                nuevas["categorias"] += creada
        self.stdout.write(self.style.SUCCESS(
            f"Catálogos listos. Nuevos: {nuevas['facultades']} facultades, {nuevas['deportes']} deportes, {nuevas['categorias']} categorías "
            f"(total: {Facultad.objects.count()}, {Deporte.objects.count()}, {Categoria.objects.count()})."))
