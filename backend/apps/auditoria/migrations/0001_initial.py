import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Bitacora",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "usuario_email",
                    models.CharField(blank=True, max_length=254),
                ),
                (
                    "accion",
                    models.CharField(
                        choices=[
                            ("LOGIN", "Inicio de sesión"),
                            ("LOGIN_FALLIDO", "Inicio de sesión fallido"),
                            ("CUENTA_BLOQUEADA", "Cuenta bloqueada"),
                            ("LOGOUT", "Cierre de sesión"),
                            ("CAMBIO_PASSWORD", "Cambio de contraseña"),
                            ("CREAR", "Crear"),
                            ("EDITAR", "Editar"),
                            ("ELIMINAR", "Eliminar"),
                            ("CAMBIO_ROL", "Cambio de rol"),
                            ("CAMBIO_ESTADO", "Cambio de estado"),
                            ("GENERAR_FIXTURE", "Generar fixture"),
                            ("REGISTRAR_RESULTADO", "Registrar resultado"),
                            ("CORREGIR_RESULTADO", "Corregir resultado"),
                            ("REGISTRAR_INCIDENCIA", "Registrar incidencia"),
                            ("EXPORTAR", "Exportar"),
                            ("ML_PRED", "Predicción ML"),
                            ("ACCESO_DENEGADO", "Acceso denegado"),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                (
                    "entidad",
                    models.CharField(blank=True, db_index=True, max_length=50),
                ),
                ("entidad_id", models.PositiveIntegerField(blank=True, null=True)),
                ("descripcion", models.TextField(blank=True)),
                ("detalle", models.JSONField(blank=True, default=dict)),
                (
                    "resultado",
                    models.CharField(
                        choices=[
                            ("OK", "Correcto"),
                            ("DENEGADO", "Denegado"),
                            ("ERROR", "Error"),
                        ],
                        db_index=True,
                        default="OK",
                        max_length=10,
                    ),
                ),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("fecha", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "usuario",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="registros_bitacora",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Bitácora",
                "verbose_name_plural": "Bitácora",
                "ordering": ["-fecha"],
            },
        ),
    ]
