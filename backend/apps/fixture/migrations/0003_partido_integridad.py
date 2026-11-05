from datetime import timedelta

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField
from django.contrib.postgres.fields.ranges import RangeOperators
from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations, models
from django.db.models import F, Func, Q


def completar_fecha_fin(apps, schema_editor):
    Partido = apps.get_model("fixture", "Partido")
    registros = []
    for partido in Partido.objects.only("pk", "fecha_hora", "duracion_min").iterator():
        partido.fecha_hora_fin = partido.fecha_hora + timedelta(
            minutes=partido.duracion_min
        )
        registros.append(partido)
        if len(registros) == 500:
            Partido.objects.bulk_update(registros, ["fecha_hora_fin"])
            registros.clear()
    if registros:
        Partido.objects.bulk_update(registros, ["fecha_hora_fin"])


class Migration(migrations.Migration):

    dependencies = [
        ("fixture", "0002_initial"),
    ]

    operations = [
        BtreeGistExtension(),
        migrations.AddField(
            model_name="partido",
            name="duracion_min",
            field=models.PositiveSmallIntegerField(default=90),
        ),
        migrations.AddField(
            model_name="partido",
            name="fecha_hora_fin",
            field=models.DateTimeField(null=True),
        ),
        migrations.RunPython(completar_fecha_fin, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="partido",
            name="fecha_hora_fin",
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name="partido",
            name="estado",
            field=models.CharField(
                choices=[
                    ("PROGRAMADO", "Programado"),
                    ("EN_CURSO", "En curso"),
                    ("FINALIZADO", "Finalizado"),
                    ("SUSPENDIDO", "Suspendido"),
                    ("POSTERGADO", "Postergado"),
                    ("WALKOVER", "Walkover (W.O.)"),
                ],
                default="PROGRAMADO",
                max_length=15,
            ),
        ),
        migrations.AddConstraint(
            model_name="partido",
            constraint=models.CheckConstraint(
                check=~Q(equipo_local=F("equipo_visitante")),
                name="partido_equipos_distintos",
            ),
        ),
        migrations.AddConstraint(
            model_name="partido",
            constraint=models.CheckConstraint(
                check=Q(duracion_min__gt=0),
                name="partido_duracion_positiva",
            ),
        ),
        migrations.AddConstraint(
            model_name="partido",
            constraint=models.CheckConstraint(
                check=Q(fecha_hora_fin__gt=F("fecha_hora")),
                name="partido_fin_despues_inicio",
            ),
        ),
        migrations.AddConstraint(
            model_name="partido",
            constraint=models.UniqueConstraint(
                fields=("campeonato", "equipo_local", "equipo_visitante", "jornada"),
                name="partido_campeonato_equipos_jornada_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="partido",
            constraint=ExclusionConstraint(
                name="partido_cancha_sin_solapamiento",
                expressions=[
                    ("cancha", RangeOperators.EQUAL),
                    (
                        Func(
                            F("fecha_hora"),
                            F("fecha_hora_fin"),
                            function="TSTZRANGE",
                            output_field=DateTimeRangeField(),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                condition=Q(cancha__isnull=False),
            ),
        ),
    ]
