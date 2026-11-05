"""
apps/users/tests/test_auth.py
Tests de autenticación y registro de usuarios.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.users.models import Usuario


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def usuario_data():
    return {
        "email":     "test@uagrm.edu.bo",
        "nombre":    "Juan",
        "apellido":  "Pérez",
        "password":  "TestPass123!",
        "password2": "TestPass123!",
        "rol":       Usuario.Rol.JUGADOR,
    }


@pytest.fixture
def usuario_creado(db, usuario_data):
    return Usuario.objects.create_user(
        email    = usuario_data["email"],
        password = usuario_data["password"],
        nombre   = usuario_data["nombre"],
        apellido = usuario_data["apellido"],
    )


@pytest.fixture
def admin_creado(db):
    return Usuario.objects.create_user(
        email="admin@uagrm.edu.bo",
        password="AdminPass123!",
        nombre="Admin",
        apellido="DUBSS",
        rol=Usuario.Rol.ADMIN_DUBSS,
    )


# ─── Tests de registro ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRegistro:

    def test_registro_anonimo_rechazado_aunque_payload_asigne_admin(self, client, usuario_data):
        usuario_data["rol"] = Usuario.Rol.ADMIN_DUBSS
        url = reverse("auth-registro")
        response = client.post(url, usuario_data, format="json")
        assert response.status_code == 401
        assert not Usuario.objects.filter(email=usuario_data["email"]).exists()

    def test_registro_usuario_autenticado_no_admin_prohibido(
        self, client, usuario_data, usuario_creado
    ):
        client.force_authenticate(user=usuario_creado)
        response = client.post(reverse("auth-registro"), usuario_data, format="json")
        assert response.status_code == 403
        assert Usuario.objects.count() == 1

    def test_registro_delegado_prohibido(self, client, usuario_data, db):
        delegado = Usuario.objects.create_user(
            email="delegado@uagrm.edu.bo",
            password="CoordPass123!",
            nombre="Coordinador",
            apellido="Facultad",
            rol=Usuario.Rol.DELEGADO,
        )
        client.force_authenticate(user=delegado)
        response = client.post(reverse("auth-registro"), usuario_data, format="json")
        assert response.status_code == 403
        assert Usuario.objects.count() == 1

    def test_admin_crea_usuario_organizador_sin_tokens_ni_password(self, client, usuario_data, admin_creado):
        client.force_authenticate(user=admin_creado)
        usuario_data["rol"] = Usuario.Rol.ORGANIZADOR
        response = client.post(reverse("auth-registro"), usuario_data, format="json")
        assert response.status_code == 201
        assert Usuario.objects.get(email=usuario_data["email"]).rol == Usuario.Rol.ORGANIZADOR
        assert "tokens" not in response.data
        assert "password" not in response.data
        assert "password" not in response.data["usuario"]
        assert "password2" not in response.data["usuario"]

    def test_admin_passwords_no_coinciden(self, client, usuario_data, admin_creado):
        client.force_authenticate(user=admin_creado)
        usuario_data["password2"] = "OtraPassword123!"
        url = reverse("auth-registro")
        response = client.post(url, usuario_data, format="json")
        assert response.status_code == 400
        assert "password" in response.data

    def test_admin_email_duplicado(self, client, usuario_data, usuario_creado, admin_creado):
        client.force_authenticate(user=admin_creado)
        url = reverse("auth-registro")
        response = client.post(url, usuario_data, format="json")
        assert response.status_code == 400

    def test_admin_rol_inexistente(self, client, usuario_data, admin_creado):
        client.force_authenticate(user=admin_creado)
        usuario_data["rol"] = "SUPERJEFE"
        response = client.post(reverse("auth-registro"), usuario_data, format="json")
        assert response.status_code == 400
        assert "rol" in response.data

    def test_admin_no_asigna_flags_privilegiados_desde_payload(
        self, client, usuario_data, admin_creado
    ):
        client.force_authenticate(user=admin_creado)
        usuario_data.update(
            {
                "rol": Usuario.Rol.ORGANIZADOR,
                "is_superuser": True,
                "is_staff": True,
            }
        )
        response = client.post(reverse("auth-registro"), usuario_data, format="json")
        assert response.status_code == 201
        usuario = Usuario.objects.get(email=usuario_data["email"])
        assert usuario.is_superuser is False
        assert usuario.is_staff is False


# ─── Tests de login ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLogin:

    def test_login_exitoso(self, client, usuario_creado):
        url = reverse("auth-login")
        response = client.post(url, {
            "email":    usuario_creado.email,
            "password": "TestPass123!",
        }, format="json")
        assert response.status_code == 200
        assert "access"  in response.data
        assert "refresh" in response.data
        assert "usuario" in response.data
        assert response.data["usuario"]["rol"] == Usuario.Rol.DELEGADO

    def test_login_credenciales_incorrectas(self, client, usuario_creado):
        url = reverse("auth-login")
        response = client.post(url, {
            "email":    usuario_creado.email,
            "password": "WrongPassword",
        }, format="json")
        assert response.status_code == 401

    def test_login_usuario_inactivo(self, client, usuario_creado):
        usuario_creado.is_active = False
        usuario_creado.save()
        url = reverse("auth-login")
        response = client.post(url, {
            "email":    usuario_creado.email,
            "password": "TestPass123!",
        }, format="json")
        assert response.status_code == 401


# ─── Tests de perfil ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPerfil:

    def test_obtener_perfil_autenticado(self, client, usuario_creado):
        client.force_authenticate(user=usuario_creado)
        url = reverse("usuario-perfil")
        response = client.get(url)
        assert response.status_code == 200
        assert response.data["email"] == usuario_creado.email

    def test_obtener_perfil_sin_autenticar(self, client):
        url = reverse("usuario-perfil")
        response = client.get(url)
        assert response.status_code == 401

    def test_patch_perfil_no_cambia_rol(self, client, usuario_creado):
        client.force_authenticate(user=usuario_creado)
        response = client.patch(
            reverse("usuario-perfil"),
            {"rol": Usuario.Rol.ADMIN_DUBSS},
            format="multipart",
        )
        usuario_creado.refresh_from_db()
        assert response.status_code == 200
        assert usuario_creado.rol == Usuario.Rol.DELEGADO

    def test_patch_perfil_no_cambia_facultad(self, client, usuario_creado):
        client.force_authenticate(user=usuario_creado)
        response = client.patch(
            reverse("usuario-perfil"),
            {"facultad": "OTRA FACULTAD"},
            format="multipart",
        )
        usuario_creado.refresh_from_db()
        assert response.status_code == 200
        assert usuario_creado.facultad is None

    def test_patch_perfil_no_cambia_is_active(self, client, usuario_creado):
        client.force_authenticate(user=usuario_creado)
        response = client.patch(
            reverse("usuario-perfil"),
            {"is_active": "false"},
            format="multipart",
        )
        usuario_creado.refresh_from_db()
        assert response.status_code == 200
        assert usuario_creado.is_active is True

    def test_patch_perfil_permite_editar_telefono(self, client, usuario_creado):
        client.force_authenticate(user=usuario_creado)
        response = client.patch(
            reverse("usuario-perfil"),
            {"telefono": "70000000"},
            format="multipart",
        )
        usuario_creado.refresh_from_db()
        assert response.status_code == 200
        assert usuario_creado.telefono == "70000000"


@pytest.mark.django_db
class TestUsuariosAdmin:

    def test_admin_cambia_rol_de_otro_usuario(self, client, admin_creado, usuario_creado):
        client.force_authenticate(user=admin_creado)
        response = client.patch(
            reverse("usuario-detalle", kwargs={"pk": usuario_creado.pk}),
            {"rol": Usuario.Rol.ORGANIZADOR},
            format="multipart",
        )
        usuario_creado.refresh_from_db()
        assert response.status_code == 200
        assert usuario_creado.rol == Usuario.Rol.ORGANIZADOR

    @pytest.mark.parametrize("rol", [Usuario.Rol.JUGADOR, Usuario.Rol.DELEGADO])
    def test_usuario_no_admin_no_puede_editar_detalle(
        self, client, usuario_creado, rol, db
    ):
        solicitante = Usuario.objects.create_user(
            email=f"{rol.lower()}@uagrm.edu.bo",
            password="RolePass123!",
            nombre="Usuario",
            apellido="Rol",
            rol=rol,
        )
        client.force_authenticate(user=solicitante)
        response = client.patch(
            reverse("usuario-detalle", kwargs={"pk": usuario_creado.pk}),
            {"rol": Usuario.Rol.ORGANIZADOR},
            format="multipart",
        )
        assert response.status_code == 403

    def test_admin_no_puede_cambiar_su_propio_rol(self, client, admin_creado):
        client.force_authenticate(user=admin_creado)
        response = client.patch(
            reverse("usuario-detalle", kwargs={"pk": admin_creado.pk}),
            {"rol": Usuario.Rol.ORGANIZADOR},
            format="multipart",
        )
        admin_creado.refresh_from_db()
        assert response.status_code == 400
        assert admin_creado.rol == Usuario.Rol.ADMIN_DUBSS

    def test_admin_no_puede_desactivarse_a_si_mismo(self, client, admin_creado):
        client.force_authenticate(user=admin_creado)
        response = client.patch(
            reverse("usuario-detalle", kwargs={"pk": admin_creado.pk}),
            {"is_active": "false"},
            format="multipart",
        )
        admin_creado.refresh_from_db()
        assert response.status_code == 400
        assert admin_creado.is_active is True

    def test_admin_no_puede_darse_de_baja(self, client, admin_creado):
        client.force_authenticate(user=admin_creado)
        response = client.delete(
            reverse("usuario-detalle", kwargs={"pk": admin_creado.pk})
        )
        admin_creado.refresh_from_db()
        assert response.status_code == 400
        assert admin_creado.is_active is True

    def test_admin_puede_dar_de_baja_a_otro_usuario(
        self, client, admin_creado, usuario_creado
    ):
        client.force_authenticate(user=admin_creado)
        response = client.delete(
            reverse("usuario-detalle", kwargs={"pk": usuario_creado.pk})
        )
        usuario_creado.refresh_from_db()
        assert response.status_code == 200
        assert usuario_creado.is_active is False
