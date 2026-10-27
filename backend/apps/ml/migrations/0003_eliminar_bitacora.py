from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("auditoria", "0002_migrar_bitacora_ml"),
        ("ml", "0002_initial"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Bitacora",
        ),
    ]
