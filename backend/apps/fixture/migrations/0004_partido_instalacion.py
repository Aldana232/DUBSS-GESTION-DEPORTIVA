import django.db.models.deletion
from django.db import migrations, models


def completar_instalacion(apps, schema_editor):
    Partido = apps.get_model("fixture", "Partido")
    registros = []
    partidos = Partido.objects.select_related("cancha").filter(cancha__isnull=False)
    for partido in partidos.iterator():
        partido.instalacion_id = partido.cancha.instalacion_id
        registros.append(partido)
        if len(registros) == 500:
            Partido.objects.bulk_update(registros, ["instalacion"])
            registros.clear()
    if registros:
        Partido.objects.bulk_update(registros, ["instalacion"])


class Migration(migrations.Migration):

    dependencies = [
        ("instalaciones", "0003_horariocancha_remove_instalacion_activa_and_more"),
        ("fixture", "0003_partido_integridad"),
    ]

    operations = [
        migrations.AddField(
            model_name="partido",
            name="instalacion",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="partidos",
                to="instalaciones.instalacion",
            ),
        ),
        migrations.RunPython(completar_instalacion, migrations.RunPython.noop),
    ]
