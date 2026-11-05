"""
apps/agente/services/acciones.py
F7-02 — Confirmar, cancelar y expirar acciones pendientes.

Solo al confirmar se escribe en el sistema, dentro de `transaction.atomic()` y revalidando TODO contra el
calendario real (pasó tiempo desde la propuesta: otro organizador pudo mover o jugar un partido).
Lo que se ejecuta es lo guardado en la acción, nunca lo que el modelo diga después.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.agente.models import AccionPendiente
from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from apps.deportes.models import Campeonato
from apps.fixture.models import Partido
from apps.fixture.services.programacion import detectar_conflictos
from apps.instalaciones.models import Cancha
from apps.notificaciones.services import notificar_usuarios
from apps.users.models import Usuario
from apps.users.roles import es_admin, es_organizador

logger = logging.getLogger(__name__)


class AccionNoEjecutable(Exception):
    """No se puede confirmar (estado, vigencia o permisos). Lleva el código HTTP sugerido."""

    def __init__(self, mensaje: str, codigo: int = 409, extra: dict | None = None):
        super().__init__(mensaje)
        self.mensaje, self.codigo, self.extra = mensaje, codigo, extra or {}


def _cerrar(accion: AccionPendiente, estado: str, resultado: dict | None = None):
    accion.estado = estado
    accion.resultado = resultado or {}
    accion.resuelta_en = timezone.now()
    accion.save(update_fields=["estado", "resultado", "resuelta_en"])


def _bloquear(accion_id: int, usuario: Usuario) -> AccionPendiente:
    """La acción de esta persona, bloqueada: dos clics seguidos no ejecutan dos veces."""
    accion = AccionPendiente.objects.select_for_update().filter(pk=accion_id, usuario=usuario).first()
    if accion is None:
        raise AccionNoEjecutable("No existe esa acción.", 404)
    return accion


def cancelar(accion_id: int, usuario: Usuario) -> AccionPendiente:
    with transaction.atomic():
        accion = _bloquear(accion_id, usuario)
        if accion.estado != AccionPendiente.Estado.PENDIENTE:
            raise AccionNoEjecutable(f"La acción ya está {accion.get_estado_display().lower()}.")
        _cerrar(accion, AccionPendiente.Estado.CANCELADA)
    registrar(Bitacora.Accion.AGENTE, usuario=usuario, modulo="agente", objeto_id=accion.pk,
              descripcion="Acción del agente cancelada por la persona.", detalle={"herramienta": accion.herramienta})
    return accion


def expirar_vencidas() -> int:
    """Marca como expiradas las acciones que nadie confirmó a tiempo (tarea periódica)."""
    return AccionPendiente.objects.filter(estado=AccionPendiente.Estado.PENDIENTE, expira_en__lte=timezone.now()).update(
        estado=AccionPendiente.Estado.EXPIRADA, resuelta_en=timezone.now())


def confirmar(accion_id: int, usuario: Usuario) -> AccionPendiente:
    if not (es_admin(usuario) or es_organizador(usuario)):
        raise AccionNoEjecutable("Tu rol ya no permite confirmar acciones del agente.", 403)
    aviso, fallo = None, None
    with transaction.atomic():
        accion = _bloquear(accion_id, usuario)
        if accion.estado != AccionPendiente.Estado.PENDIENTE:
            raise AccionNoEjecutable(f"La acción ya está {accion.get_estado_display().lower()}.")
        ejecutor = {"aplicar_reprogramacion": _ejecutar_reprogramacion, "enviar_notificacion": _ejecutar_notificacion}.get(accion.herramienta)
        if ejecutor is None:
            raise AccionNoEjecutable("Esta acción no se puede ejecutar.", 400)
        # Los desenlaces «no se pudo» se registran en la acción y se informan DESPUÉS de la transacción
        # (lanzar dentro la deshacería y se perdería la constancia).
        if accion.expira_en <= timezone.now():
            _cerrar(accion, AccionPendiente.Estado.EXPIRADA)
            fallo = AccionNoEjecutable("La acción venció. Pídele al agente que la calcule de nuevo.", 410)
        else:
            try:
                resultado, aviso = ejecutor(accion, usuario)
            except AccionNoEjecutable as e:        # el calendario cambió desde la propuesta: no se aplicó nada
                _cerrar(accion, AccionPendiente.Estado.FALLIDA, {"error": e.mensaje, **e.extra})
                fallo = e
            else:
                _cerrar(accion, AccionPendiente.Estado.CONFIRMADA, resultado)
    if fallo is not None:
        registrar(Bitacora.Accion.AGENTE, usuario=usuario, modulo="agente", objeto_id=accion.pk, resultado="ERROR",
                  descripcion="Acción del agente rechazada al confirmar.", detalle={"herramienta": accion.herramienta, "motivo": fallo.mensaje})
        raise fallo
    registrar(Bitacora.Accion.AGENTE, usuario=usuario, modulo="agente", objeto_id=accion.pk,
              descripcion="Acción del agente confirmada y ejecutada.", detalle={"herramienta": accion.herramienta, **accion.resultado})
    if aviso:
        aviso()           # los avisos salen DESPUÉS de confirmar la transacción
    return accion


# ── Reprogramación ────────────────────────────────────────────────────────────

def _t(valor: str) -> datetime:
    return datetime.fromisoformat(valor)


def _ejecutar_reprogramacion(accion: AccionPendiente, usuario: Usuario):
    cambios = accion.propuesta["cambios"]
    ids = [c["partido_id"] for c in cambios]
    partidos = {p.pk: p for p in Partido.objects.select_for_update(of=("self",)).select_related("campeonato", "equipo_local", "equipo_visitante", "cancha")
                .filter(pk__in=ids)}

    # 1) Nada cambió desde la propuesta.
    obsoletos = []
    for c in cambios:
        p = partidos.get(c["partido_id"])
        if p is None:
            obsoletos.append(f"{c['partido']}: ya no existe.")
        elif p.estado != Partido.Estado.PROGRAMADO:
            obsoletos.append(f"{c['partido']}: ahora está «{p.get_estado_display()}».")
        elif p.campeonato.estado != Campeonato.Estado.EN_CURSO:
            obsoletos.append(f"{c['partido']}: su campeonato ya no está en curso.")
        elif p.fecha_hora != _t(c["anterior"]["inicio"]) or p.cancha_id != c["anterior"]["cancha_id"]:
            obsoletos.append(f"{c['partido']}: alguien lo reprogramó mientras tanto.")
    if obsoletos:
        raise AccionNoEjecutable("El calendario cambió desde la propuesta: " + " ".join(obsoletos), extra={"conflictos": obsoletos})

    # 2) El estado FINAL es válido: cada partido contra el resto del calendario (sin contar los que se mueven)…
    canchas = {c.pk: c for c in Cancha.objects.filter(pk__in={c["nuevo"]["cancha_id"] for c in cambios})}
    conflictos = []
    for c in cambios:
        p = partidos[c["partido_id"]]
        cancha = canchas.get(c["nuevo"]["cancha_id"])
        if cancha is None:
            conflictos.append(f"{c['partido']}: la cancha elegida ya no existe.")
            continue
        conflictos += [f"{c['partido']}: {m}" for m in detectar_conflictos(
            cancha=cancha, fecha_hora=_t(c["nuevo"]["inicio"]), duracion_min=p.duracion_min,
            equipo_local=p.equipo_local, equipo_visitante=p.equipo_visitante, excluir_ids=ids)]
    # …y los partidos movidos tampoco chocan entre sí.
    for i, a in enumerate(cambios):
        for b in cambios[i + 1:]:
            if not (_t(a["nuevo"]["inicio"]) < _t(b["nuevo"]["fin"]) and _t(b["nuevo"]["inicio"]) < _t(a["nuevo"]["fin"])):
                continue
            pa, pb = partidos[a["partido_id"]], partidos[b["partido_id"]]
            if a["nuevo"]["cancha_id"] == b["nuevo"]["cancha_id"]:
                conflictos.append(f"{a['partido']} y {b['partido']} quedarían en la misma cancha a la vez.")
            if {pa.equipo_local_id, pa.equipo_visitante_id} & {pb.equipo_local_id, pb.equipo_visitante_id}:
                conflictos.append(f"{a['partido']} y {b['partido']} comparten un equipo a la misma hora.")
    if conflictos:
        raise AccionNoEjecutable("Ya no es posible aplicar la propuesta: " + " ".join(conflictos[:6]), extra={"conflictos": conflictos})

    # 3) Se aplica en dos fases: primero se liberan las canchas (la base prohíbe solapes de cancha incluso a mitad
    #    de la operación, y dos partidos pueden intercambiar horarios), luego se asigna el destino.
    Partido.objects.filter(pk__in=ids).update(cancha=None, instalacion=None)
    avisos = defaultdict(list)
    for c in cambios:
        p = partidos[c["partido_id"]]
        antes = f"{timezone.localtime(_t(c['anterior']['inicio'])):%d/%m %H:%M} en {c['anterior']['cancha'] or 'sin cancha'}"
        p.cancha = canchas[c["nuevo"]["cancha_id"]]
        p.instalacion = None
        p.fecha_hora = _t(c["nuevo"]["inicio"])
        nota = f"Reprogramado por el agente ({accion.propuesta['motivo']})."
        p.observaciones = f"{p.observaciones}\n{nota}".strip()
        p.save()
        despues = f"{timezone.localtime(p.fecha_hora):%d/%m %H:%M} en {p.cancha.nombre}"
        registrar(Bitacora.Accion.EDITAR, usuario=usuario, modulo="partido", objeto_id=p.pk, descripcion="Partido reprogramado.",
                  detalle={"via": "agente", "accion": accion.pk, "motivo": accion.propuesta["motivo"],
                           "anterior": c["anterior"], "nuevo": {"cancha_id": c["nuevo"]["cancha_id"], "fecha_hora": c["nuevo"]["inicio"]}})
        for equipo in (p.equipo_local, p.equipo_visitante):
            if equipo.delegado_id:
                avisos[equipo.delegado_id].append(f"{p.equipo_local.nombre} vs {p.equipo_visitante.nombre}: de {antes} a {despues}.")

    def notificar():
        usuarios = {u.pk: u for u in Usuario.objects.filter(pk__in=avisos)}
        resumen = {"usuarios": 0, "email": 0, "push": 0}
        for uid, lineas in avisos.items():
            r = notificar_usuarios([usuarios[uid]] if uid in usuarios else [], "Partido reprogramado",
                                   f"Motivo: {accion.propuesta['motivo']}. " + " ".join(lineas)[:450])
            for k in resumen:
                resumen[k] += r[k]
        accion.resultado = {**accion.resultado, "notificados": resumen}
        accion.save(update_fields=["resultado"])

    resultado = {"partidos_reprogramados": len(cambios), "delegados_avisados": len(avisos), "partidos": ids}
    return resultado, notificar


# ── Aviso ─────────────────────────────────────────────────────────────────────

def _ejecutar_notificacion(accion: AccionPendiente, usuario: Usuario):
    p = accion.propuesta
    usuarios = list(Usuario.objects.filter(pk__in=p["usuarios"], is_active=True))
    if not usuarios:
        raise AccionNoEjecutable("Ya no hay usuarios activos entre los destinatarios.")
    resultado = {"destinatarios": len(usuarios), "titulo": p["titulo"]}

    def enviar():
        r = notificar_usuarios(usuarios, p["titulo"], p["mensaje"])
        accion.resultado = {**accion.resultado, "email": r["email"], "push": r["push"]}
        accion.save(update_fields=["resultado"])
    return resultado, enviar
