from django.utils import timezone

from .models import (
    Campeonato,
    FichaJugador,
    Inscripcion,
    RestriccionHorarioFacultad,
)


def facultad_tiene_restriccion(facultad_ids, fecha_hora, duracion) -> bool:
    if timezone.is_naive(fecha_hora):
        raise ValueError("La fecha y hora deben incluir zona horaria.")
    if duracion.total_seconds() <= 0:
        raise ValueError("La duración debe ser positiva.")

    fecha_fin = fecha_hora + duracion
    inicio_local = timezone.localtime(fecha_hora)
    fin_local = timezone.localtime(fecha_fin)
    if inicio_local.date() != fin_local.date():
        return True

    return RestriccionHorarioFacultad.objects.filter(
        facultad_id__in=facultad_ids,
        dia_semana=inicio_local.weekday(),
        hora_inicio__lt=fin_local.time().replace(tzinfo=None),
        hora_fin__gt=inicio_local.time().replace(tzinfo=None),
    ).exists()


def motivos_ficha(ficha: FichaJugador, inscripcion: Inscripcion) -> list[tuple[str, str]]:
    """Motivos (código, mensaje) por los que una ficha no puede competir."""
    motivos = []
    if ficha.equipo_id != inscripcion.equipo_id:
        motivos.append(("pertenencia", "La ficha no pertenece al equipo de la inscripción."))

    duplicada = FichaJugador.objects.filter(
        carnet=ficha.carnet,
        equipo__inscripciones__campeonato=inscripcion.campeonato,
    ).exclude(pk=ficha.pk)
    if duplicada.exists():
        motivos.append(
            ("duplicada", "El jugador ya está inscrito en otro equipo del campeonato.")
        )

    if ficha.partidos_sancion_restantes > 0:
        motivos.append((
            "sancion",
            f"El jugador tiene {ficha.partidos_sancion_restantes} partido(s) de sanción pendiente(s).",
        ))
    return motivos


def motivos_equipo(
    inscripcion: Inscripcion, *, verificar_plazo: bool = True
) -> list[tuple[str, str]]:
    """Motivos (código, mensaje) a nivel de equipo/campeonato."""
    motivos = []
    campeonato = inscripcion.campeonato
    cantidad_jugadores = FichaJugador.objects.filter(
        equipo=inscripcion.equipo,
        estado="ACTIVO",
    ).count()
    if cantidad_jugadores < campeonato.min_jugadores:
        motivos.append((
            "minimo",
            f"El equipo no alcanza el mínimo de {campeonato.min_jugadores} jugadores.",
        ))
    if cantidad_jugadores > campeonato.max_jugadores:
        motivos.append((
            "maximo",
            f"El equipo supera el máximo de {campeonato.max_jugadores} jugadores.",
        ))

    if verificar_plazo:
        cierre = campeonato.fecha_cierre_inscripcion
        if cierre is not None and timezone.now() >= cierre:
            motivos.append(("plazo", "El plazo de inscripción del campeonato ha cerrado."))
        if campeonato.estado != campeonato.Estado.INSCRIPCIONES:
            motivos.append(("estado", "El campeonato no está recibiendo inscripciones."))
    return motivos


def validar_elegibilidad(ficha: FichaJugador, inscripcion: Inscripcion) -> list[str]:
    motivos = motivos_ficha(ficha, inscripcion) + motivos_equipo(inscripcion)
    return [mensaje for _, mensaje in motivos]


# Motivos que impiden aprobar la inscripción; los demás son advertencias
# (por ejemplo, un jugador sancionado no puede jugar pero no invalida al equipo).
MOTIVOS_BLOQUEANTES = {"pertenencia", "duplicada", "minimo", "maximo", "cupo"}


def evaluar_inscripcion(inscripcion: Inscripcion) -> dict:
    """
    Revisa si una inscripción PENDIENTE puede aprobarse (F3-02).
    El plazo y el estado del campeonato se validan al solicitar, no al aprobar.
    """
    campeonato = inscripcion.campeonato
    bloqueantes: list[str] = []
    advertencias: list[str] = []

    aprobadas = Inscripcion.objects.filter(
        campeonato=campeonato, estado=Inscripcion.Estado.APROBADA
    ).exclude(pk=inscripcion.pk).count()
    if aprobadas >= campeonato.max_equipos:
        bloqueantes.append(
            f"El campeonato ya alcanzó el máximo de {campeonato.max_equipos} equipos."
        )

    for codigo, mensaje in motivos_equipo(inscripcion, verificar_plazo=False):
        (bloqueantes if codigo in MOTIVOS_BLOQUEANTES else advertencias).append(mensaje)

    fichas = FichaJugador.objects.filter(equipo=inscripcion.equipo, estado="ACTIVO")
    for ficha in fichas:
        for codigo, mensaje in motivos_ficha(ficha, inscripcion):
            texto = f"{ficha.nombre} {ficha.apellido}: {mensaje}"
            (bloqueantes if codigo in MOTIVOS_BLOQUEANTES else advertencias).append(texto)

    return {"bloqueantes": bloqueantes, "advertencias": advertencias}


# ── Máquina de estados del campeonato (F3-01, RF10) ──────────────────────────

E = Campeonato.Estado
TRANSICIONES_CAMPEONATO = {
    E.PLANIFICACION: {E.INSCRIPCIONES, E.CANCELADO},
    E.INSCRIPCIONES: {E.PLANIFICACION, E.INSCRIPCION_CERRADA, E.CANCELADO},
    E.INSCRIPCION_CERRADA: {E.INSCRIPCIONES, E.EN_CURSO, E.CANCELADO},
    E.EN_CURSO: {E.FINALIZADO, E.CANCELADO},
    E.FINALIZADO: set(),
    E.CANCELADO: set(),
}
del E


def transiciones_permitidas(estado: str) -> list[str]:
    destinos = TRANSICIONES_CAMPEONATO.get(estado, set())
    return [e for e in Campeonato.Estado.values if e in destinos]


def errores_transicion_campeonato(campeonato: Campeonato, nuevo: str) -> list[str]:
    """Devuelve los motivos por los que no se puede pasar al estado `nuevo`."""
    from apps.fixture.models import Partido

    E = Campeonato.Estado
    if nuevo not in Campeonato.Estado.values:
        return [f"Estado inválido. Opciones: {list(Campeonato.Estado.values)}."]
    if nuevo == campeonato.estado:
        return ["El campeonato ya se encuentra en ese estado."]
    if nuevo not in TRANSICIONES_CAMPEONATO.get(campeonato.estado, set()):
        permitidas = transiciones_permitidas(campeonato.estado)
        detalle = ", ".join(permitidas) if permitidas else "ninguna (estado final)"
        return [
            f"No se puede pasar de {campeonato.estado} a {nuevo}. "
            f"Transiciones permitidas: {detalle}."
        ]

    errores = []
    aprobadas = Inscripcion.objects.filter(
        campeonato=campeonato, estado=Inscripcion.Estado.APROBADA
    ).count()
    if nuevo in (E.INSCRIPCION_CERRADA, E.EN_CURSO) and aprobadas < 2:
        errores.append("Se necesitan al menos 2 equipos con inscripción aprobada.")
    if nuevo == E.EN_CURSO and not Partido.objects.filter(campeonato=campeonato).exists():
        errores.append("Genera el fixture antes de iniciar el campeonato.")
    if (
        nuevo == E.INSCRIPCIONES
        and campeonato.estado == E.INSCRIPCION_CERRADA
        and Partido.objects.filter(campeonato=campeonato).exists()
    ):
        errores.append(
            "El campeonato ya tiene fixture: no se pueden reabrir las inscripciones "
            "porque dejaría fuera a los equipos nuevos."
        )
    if nuevo == E.FINALIZADO:
        pendientes = Partido.objects.filter(campeonato=campeonato).exclude(
            estado__in=[Partido.Estado.FINALIZADO, Partido.Estado.WALKOVER]
        ).count()
        if pendientes:
            errores.append(f"Hay {pendientes} partido(s) sin resultado registrado.")
    return errores
