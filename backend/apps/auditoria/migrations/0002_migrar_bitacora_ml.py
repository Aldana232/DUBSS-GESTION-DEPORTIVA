from django.db import migrations


ACCIONES_VALIDAS = {
    "LOGIN",
    "LOGIN_FALLIDO",
    "CUENTA_BLOQUEADA",
    "LOGOUT",
    "CAMBIO_PASSWORD",
    "CREAR",
    "EDITAR",
    "ELIMINAR",
    "CAMBIO_ROL",
    "CAMBIO_ESTADO",
    "GENERAR_FIXTURE",
    "REGISTRAR_RESULTADO",
    "CORREGIR_RESULTADO",
    "REGISTRAR_INCIDENCIA",
    "EXPORTAR",
    "ML_PRED",
    "ACCESO_DENEGADO",
}


def migrar_bitacora(apps, schema_editor):
    BitacoraAnterior = apps.get_model("ml", "Bitacora")
    BitacoraNueva = apps.get_model("auditoria", "Bitacora")
    alias = schema_editor.connection.alias

    registros = BitacoraAnterior.objects.using(alias).values(
        "id",
        "usuario_id",
        "usuario__email",
        "accion",
        "modulo",
        "descripcion",
        "objeto_id",
        "ip_address",
        "timestamp",
    )
    for registro in registros.iterator():
        nueva = BitacoraNueva.objects.using(alias).create(
            usuario_id=registro["usuario_id"],
            usuario_email=registro["usuario__email"] or "",
            accion=(
                registro["accion"]
                if registro["accion"] in ACCIONES_VALIDAS
                else "EDITAR"
            ),
            entidad=registro["modulo"],
            entidad_id=registro["objeto_id"],
            descripcion=registro["descripcion"],
            ip_address=registro["ip_address"],
        )
        BitacoraNueva.objects.using(alias).filter(pk=nueva.pk).update(
            fecha=registro["timestamp"]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("auditoria", "0001_initial"),
        ("ml", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(migrar_bitacora, migrations.RunPython.noop),
    ]
