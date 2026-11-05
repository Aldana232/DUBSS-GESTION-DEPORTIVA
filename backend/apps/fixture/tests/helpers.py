"""Constructores de escenarios para los tests de la Fase 3."""
from datetime import date, time
from types import SimpleNamespace
from itertools import count

from rest_framework.test import APIClient

from apps.deportes.models import (
    Campeonato, Categoria, Deporte, Equipo, Facultad, FichaJugador, Inscripcion,
)
from apps.instalaciones.models import Cancha, HorarioCancha, Instalacion
from apps.users.models import Usuario

_contador = count(1)


def crear_usuario(rol, facultad=None, prefijo="u"):
    n = next(_contador)
    return Usuario.objects.create_user(
        email=f"{prefijo}{n}@example.com",
        password="PruebaSegura123!",
        nombre=f"Nombre{n}",
        apellido=f"Apellido{n}",
        rol=rol,
        facultad=facultad,
    )


def cliente_de(usuario):
    cliente = APIClient()
    cliente.force_authenticate(usuario)
    return cliente


def crear_canchas(deporte, cantidad=2, hora_inicio=time(8), hora_fin=time(22)):
    n = next(_contador)
    instalacion = Instalacion.objects.create(nombre=f"Instalación {n}", ubicacion="Campus")
    canchas = []
    for i in range(cantidad):
        cancha = Cancha.objects.create(
            instalacion=instalacion, nombre=f"Cancha {n}-{i + 1}", deporte=deporte
        )
        for dia in range(7):
            HorarioCancha.objects.create(
                cancha=cancha, dia_semana=dia, hora_inicio=hora_inicio, hora_fin=hora_fin
            )
        canchas.append(cancha)
    return canchas


def crear_equipo(nombre, campeonato=None, estado_inscripcion=Inscripcion.Estado.APROBADA,
                 jugadores=0, delegado=True):
    n = next(_contador)
    facultad = Facultad.objects.create(nombre=f"Facultad {nombre} {n}", sigla=f"F{n}")
    equipo = Equipo.objects.create(nombre=nombre, facultad=facultad)
    if delegado:
        equipo.delegado = crear_usuario(Usuario.Rol.DELEGADO, facultad, prefijo="del")
        equipo.save(update_fields=["delegado"])
    for i in range(jugadores):
        crear_jugador(equipo, i + 1)
    if campeonato is not None:
        Inscripcion.objects.create(
            campeonato=campeonato, equipo=equipo, estado=estado_inscripcion
        )
    return equipo


def crear_jugador(equipo, numero, carnet=None):
    n = next(_contador)
    return FichaJugador.objects.create(
        equipo=equipo,
        nombre=f"Jugador{n}",
        apellido="Prueba",
        carnet=carnet or f"CI{n}",
        registro=f"REG{n}",
        posicion="Delantero",
        numero_camiseta=numero,
    )


def crear_campeonato(deporte=None, formato=Campeonato.Formato.LIGA,
                     estado=Campeonato.Estado.INSCRIPCIONES,
                     fecha_inicio=date(2027, 3, 1), **extra):
    n = next(_contador)
    deporte = deporte or Deporte.objects.create(nombre=f"Deporte {n}")
    categoria = Categoria.objects.create(deporte=deporte, nombre=f"Categoría {n}")
    return Campeonato.objects.create(
        nombre=f"Campeonato {n}",
        categoria=categoria,
        formato=formato,
        estado=estado,
        fecha_inicio=fecha_inicio,
        fecha_fin=date(2027, 12, 31),
        max_equipos=extra.pop("max_equipos", 32),
        **extra,
    )


def crear_escenario(equipos=4, canchas=2, **kwargs):
    """Campeonato con `equipos` inscripciones aprobadas y `canchas` canchas abiertas."""
    # Los escenarios de fixture parten con inscripciones cerradas (RF11).
    kwargs.setdefault("estado", Campeonato.Estado.INSCRIPCION_CERRADA)
    campeonato = crear_campeonato(**kwargs)
    deporte = campeonato.categoria.deporte
    lista_canchas = crear_canchas(deporte, canchas) if canchas else []
    lista_equipos = [
        crear_equipo(f"Equipo {i + 1}", campeonato) for i in range(equipos)
    ]
    admin = crear_usuario(Usuario.Rol.ADMIN_DUBSS, prefijo="admin")
    organizador = crear_usuario(Usuario.Rol.ORGANIZADOR, prefijo="org")
    return SimpleNamespace(
        campeonato=campeonato,
        deporte=deporte,
        equipos=lista_equipos,
        canchas=lista_canchas,
        admin=admin,
        organizador=organizador,
        client=cliente_de(admin),
        client_org=cliente_de(organizador),
    )


def hay_solapes(partidos):
    """Devuelve una descripción del primer solape de cancha o de equipo, o None."""
    partidos = list(partidos)
    for i, a in enumerate(partidos):
        for b in partidos[i + 1:]:
            if not (a.fecha_hora < b.fecha_hora_fin and b.fecha_hora < a.fecha_hora_fin):
                continue
            if a.cancha_id and a.cancha_id == b.cancha_id:
                return f"cancha {a.cancha_id}: {a} / {b}"
            equipos_a = {a.equipo_local_id, a.equipo_visitante_id} - {None}
            equipos_b = {b.equipo_local_id, b.equipo_visitante_id} - {None}
            if equipos_a & equipos_b:
                return f"equipo: {a} / {b}"
    return None
