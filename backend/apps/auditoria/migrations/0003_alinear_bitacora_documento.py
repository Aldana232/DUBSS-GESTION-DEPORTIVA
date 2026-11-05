from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("auditoria", "0002_migrar_bitacora_ml"),
    ]

    operations = [
        migrations.RenameField(
            model_name="bitacora",
            old_name="entidad",
            new_name="modulo",
        ),
        migrations.RenameField(
            model_name="bitacora",
            old_name="entidad_id",
            new_name="objeto_id",
        ),
        migrations.RenameField(
            model_name="bitacora",
            old_name="ip_address",
            new_name="ip_origen",
        ),
        migrations.RenameField(
            model_name="bitacora",
            old_name="fecha",
            new_name="fecha_hora",
        ),
        migrations.AlterModelOptions(
            name="bitacora",
            options={
                "ordering": ["-fecha_hora"],
                "verbose_name": "Bitácora",
                "verbose_name_plural": "Bitácora",
            },
        ),
    ]
