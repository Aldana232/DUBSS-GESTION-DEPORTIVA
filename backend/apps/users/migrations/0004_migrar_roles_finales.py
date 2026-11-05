from django.db import migrations


ROL_SUPERADMIN = "SUPERADMIN"
ROL_ADMIN_DUBSS = "ADMIN_DUBSS"
ROL_ORGANIZADOR = "ORGANIZADOR"
ROL_DELEGADO = "DELEGADO"
ROL_JUGADOR = "JUGADOR"

ROL_COORDINADOR = "COORDINADOR"
ROL_ARBITRO = "ARBITRO"
ROL_DEPORTISTA = "DEPORTISTA"
ROL_PUBLICO = "PUBLICO"


def migrar_roles(apps, schema_editor):
    Usuario = apps.get_model("users", "Usuario")
    usuarios = Usuario.objects.using(schema_editor.connection.alias)

    superadministradores = usuarios.filter(is_superuser=True).exclude(
        rol=ROL_SUPERADMIN
    ).update(rol=ROL_SUPERADMIN)
    delegados = usuarios.filter(rol=ROL_COORDINADOR).update(rol=ROL_DELEGADO)
    organizadores = usuarios.filter(rol=ROL_ARBITRO).update(rol=ROL_ORGANIZADOR)
    deportistas = usuarios.filter(rol=ROL_DEPORTISTA).update(
        rol=ROL_JUGADOR,
        is_active=False,
    )
    publicos = usuarios.filter(rol=ROL_PUBLICO).update(
        rol=ROL_JUGADOR,
        is_active=False,
    )
    administradores = usuarios.filter(rol=ROL_ADMIN_DUBSS).count()

    print(f"is_superuser=True -> SUPERADMIN: {superadministradores}")
    print(f"COORDINADOR -> DELEGADO: {delegados}")
    print(f"ARBITRO -> ORGANIZADOR: {organizadores}")
    print(f"DEPORTISTA -> JUGADOR inactivo: {deportistas}")
    print(f"PUBLICO -> JUGADOR inactivo: {publicos}")
    print(f"ADMIN_DUBSS conservados sin cambio: {administradores}")


def revertir_roles(apps, schema_editor):
    """No invierte roles de forma ambigua; conserva los valores migrados."""


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_actualizar_roles_finales"),
    ]

    operations = [
        migrations.RunPython(migrar_roles, revertir_roles),
    ]
