"""
Crea el primer superadministrador de una instalación nueva (producción) SIN datos de ejemplo.

    python manage.py crear_superadmin --email admin@uagrm.edu.bo --nombre Ana --apellido Pérez
    (la contraseña se pide por teclado, o se toma de la variable DUBSS_ADMIN_PASSWORD para automatizar)

Es idempotente: si el correo ya existe no cambia nada. La contraseña pasa por los validadores de Django
(longitud mínima, no demasiado común, no solo números).
"""
import getpass
import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from apps.users.models import Usuario


class Command(BaseCommand):
    help = "Crea el primer superadministrador (idempotente; la contraseña se pide o viene de DUBSS_ADMIN_PASSWORD)."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--nombre", required=True)
        parser.add_argument("--apellido", required=True)

    def handle(self, *args, email, nombre, apellido, **opciones):
        email = email.strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            raise CommandError(f"«{email}» no es un correo válido.")
        if Usuario.objects.filter(email__iexact=email).exists():
            self.stdout.write(self.style.WARNING(f"Ya existe una cuenta con {email}: no se cambió nada."))
            return

        clave = os.environ.get("DUBSS_ADMIN_PASSWORD") or self._pedir_clave()
        candidato = Usuario(email=email, nombre=nombre.strip(), apellido=apellido.strip())
        try:
            validate_password(clave, candidato)
        except ValidationError as e:
            raise CommandError("La contraseña no es segura: " + " ".join(e.messages))

        Usuario.objects.create_superuser(email=email, password=clave, nombre=nombre.strip(), apellido=apellido.strip())
        self.stdout.write(self.style.SUCCESS(f"Superadministrador {email} creado. Cambia la contraseña desde «Mi perfil» cuando quieras."))

    @staticmethod
    def _pedir_clave() -> str:
        a = getpass.getpass("Contraseña: ")
        if a != getpass.getpass("Repite la contraseña: "):
            raise CommandError("Las contraseñas no coinciden.")
        return a
