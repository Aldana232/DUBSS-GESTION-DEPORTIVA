"""
seed_realista — Datos de ejemplo que simulan la operación real de la DUBSS en la UAGRM.

Reemplaza a `seed_demo`. Qué crea (todo en español, con nombres y facultades de la UAGRM):
  * 12 facultades, deportes, categorías, 3 instalaciones con 7 canchas, horarios, un bloqueo y restricciones por clases.
  * Cuentas de todos los roles (superadmin, admin, 2 organizadores, 12 delegados, 3 jugadores con cuenta).
  * 44 equipos con sus plantillas (unos 560 jugadores).
  * Temporada 2025 completa de Fútbol y de Futsal (con resultados, goles y tarjetas) → historial para la IA.
  * Fútbol Varones 2026 EN CURSO: fixture generado por el propio sistema (optimizador), 3 jornadas jugadas y la
    cuarta programada para hoy y los próximos días (para probar la planilla móvil).
  * Copa Relámpago de Futsal (eliminación directa) lista para generar con siembra por IA, un torneo de voleibol con
    inscripciones por validar y uno de baloncesto en planificación; quejas en distintos estados.
  * Entrena el predictor y el puntuador del fixture, y busca resultados atípicos.

Vuelve a ejecutarlo para restablecer los datos de ejemplo. BORRA los datos de campeonatos, equipos, partidos, etc. y las
cuentas de ejemplo; conserva cualquier otra cuenta (por ejemplo la del programador). Solo con DEBUG=True.
"""
import math
import random
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.agente.models import ConversacionAgente
from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from apps.deportes.management.commands import _datos_uagrm as D
from apps.deportes.models import (
    Campeonato, Categoria, Deporte, Equipo, Facultad, FichaJugador, Inscripcion, RestriccionHorarioFacultad,
)
from apps.fixture.models import Incidencia, OperacionIdempotente, Partido, PosicionHistorial, Resultado, TablaPosiciones
from apps.fixture.services import resultados, sanciones, tabla
from apps.fixture.services.fixture_generator import FixtureGenerator, _round_robin
from apps.instalaciones.models import BloqueoCancha, Cancha, HorarioCancha, Instalacion
from apps.ml.models import (
    ModeloML, MuestraAsignacion, PrediccionAsistencia, PrediccionPartido, ResultadoAtipico, RiesgoClimatico,
)
from apps.notificaciones.models import RecordatorioEnviado
from apps.quejas.models import Queja
from apps.users.models import Usuario

PASSWORD = "Dubss2026!"
DOMINIOS_DE_EJEMPLO = ("@example.test", "@example.com", "@uagrm.edu.bo")
T = Incidencia.Tipo


def poisson(rng: random.Random, lam: float) -> int:
    limite, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limite:
            return k
        k += 1


class Command(BaseCommand):
    help = "Reemplaza los datos de demostración por datos realistas de la UAGRM (solo desarrollo)."

    def add_arguments(self, parser):
        parser.add_argument("--password", default=PASSWORD, help="Contraseña de todas las cuentas de ejemplo.")
        parser.add_argument("--sin-ia", action="store_true", help="No entrena los modelos al terminar (más rápido).")

    def handle(self, *args, **opciones):
        if not settings.DEBUG:
            raise CommandError("seed_realista solo puede ejecutarse con DEBUG=True.")
        self.rng = random.Random(2026)
        self.password = opciones["password"]
        self.hoy = timezone.localdate()
        self.credenciales: list[tuple[str, str, str]] = []
        with transaction.atomic():
            self._limpiar()
            self._catalogos()
            self._cuentas()
            self._instalaciones()
            self._equipos()
            self._temporadas_2025()
            self._temporada_en_curso()
            self._otros_campeonatos()
            self._quejas()
            self._jugadores_con_cuenta()
            self._bitacora()
        if not opciones["sin_ia"]:
            self._entrenar_modelos()
        self._resumen()

    # ── 0. Limpieza ───────────────────────────────────────────────────────────

    def _limpiar(self):
        self.stdout.write("Borrando datos de ejemplo anteriores...")
        for modelo in (Queja, ResultadoAtipico, PrediccionPartido, PrediccionAsistencia, RiesgoClimatico, ModeloML, RecordatorioEnviado,
                       ConversacionAgente, OperacionIdempotente, Incidencia, Resultado, PosicionHistorial, TablaPosiciones, Partido,
                       Inscripcion, FichaJugador, Equipo, Campeonato, BloqueoCancha, HorarioCancha, Cancha, Instalacion,
                       Categoria, Deporte, RestriccionHorarioFacultad, Facultad, Bitacora):
            modelo.objects.all().delete()
        MuestraAsignacion.objects.exclude(partido_id__isnull=True).delete()     # las de arranque en frío se conservan
        propias = Usuario.objects.none()
        for dominio in DOMINIOS_DE_EJEMPLO:
            propias = propias | Usuario.objects.filter(email__iendswith=dominio)
        propias.delete()

    # ── 1. Catálogos ──────────────────────────────────────────────────────────

    def _catalogos(self):
        self.facultades = {s: Facultad.objects.create(sigla=s, nombre=n) for s, n, *_ in D.FACULTADES}
        self.info = {s: {"apodo": a, "color": c, "fuerza": f, "delegado": d} for s, _, a, c, f, d in D.FACULTADES}
        self.deportes = {n: Deporte.objects.create(nombre=n, cantidad_jugadores=c, descripcion=d) for n, c, d in D.DEPORTES}
        self.categorias = {}
        for nombre, deporte in self.deportes.items():
            for genero, etiqueta in (("VARONES", "Varones"), ("DAMAS", "Damas")):
                self.categorias[(nombre, genero)] = Categoria.objects.create(
                    deporte=deporte, nombre=f"{nombre} {etiqueta}", genero=genero, rango_edad="Libre universitario",
                    descripcion=f"Categoría {etiqueta.lower()} de {nombre.lower()} para estudiantes regulares de la UAGRM.")
        for sigla, dia, (h1, m1), (h2, m2), motivo in D.RESTRICCIONES:
            RestriccionHorarioFacultad.objects.create(facultad=self.facultades[sigla], dia_semana=dia, hora_inicio=time(h1, m1), hora_fin=time(h2, m2), motivo=motivo)

    # ── 2. Cuentas ────────────────────────────────────────────────────────────

    def _usuario(self, email, nombre, apellido, rol, facultad=None, etiqueta=""):
        u = Usuario.objects.create_user(
            email=email, password=self.password, nombre=nombre, apellido=apellido, rol=rol, facultad=facultad,
            ci=f"{self.rng.randint(5_000_000, 13_999_999)} SC", telefono=f"7{self.rng.randint(1_000_000, 9_999_999)}")
        self.credenciales.append((etiqueta or u.get_rol_display(), email, f"{nombre} {apellido}"))
        return u

    def _cuentas(self):
        R = Usuario.Rol
        self.superadmin = self._usuario("superadmin@uagrm.edu.bo", "Carlos", "Mendoza Rojas", R.SUPERADMIN, etiqueta="Superadministrador")
        self.admin = self._usuario("admin@uagrm.edu.bo", "Rosa Elena", "Vargas Soliz", R.ADMIN_DUBSS, etiqueta="Administrador DUBSS")
        self.organizador = self._usuario("organizador@uagrm.edu.bo", "Luis Fernando", "Camacho Ribera", R.ORGANIZADOR, etiqueta="Organizador")
        self.organizador2 = self._usuario("organizador2@uagrm.edu.bo", "María José", "Terrazas Egüez", R.ORGANIZADOR, etiqueta="Organizador (2)")
        self.delegados = {}
        for sigla, f in self.info.items():
            nombre, apellido = f["delegado"]
            self.delegados[sigla] = self._usuario(f"delegado.{sigla.lower()}@uagrm.edu.bo", nombre, apellido, R.DELEGADO,
                                                  facultad=self.facultades[sigla], etiqueta=f"Delegado {sigla}")

    # ── 3. Instalaciones ──────────────────────────────────────────────────────

    def _instalaciones(self):
        self.canchas: dict[str, list[Cancha]] = {}
        for inst in D.INSTALACIONES:
            instalacion = Instalacion.objects.create(nombre=inst["nombre"], tipo=inst["tipo"], ubicacion=inst["ubicacion"], capacidad=inst["capacidad"])
            for nombre, deporte, superficie, capacidad, techada in inst["canchas"]:
                cancha = Cancha.objects.create(instalacion=instalacion, nombre=nombre, deporte=self.deportes[deporte], superficie=superficie,
                                               capacidad=capacidad, techada=techada)
                self.canchas.setdefault(deporte, []).append(cancha)
                for dia in range(7):
                    desde, hasta = (time(14), time(22)) if dia < 5 else (time(8), time(20))
                    HorarioCancha.objects.create(cancha=cancha, dia_semana=dia, hora_inicio=desde, hora_fin=hasta)
        auxiliar = self.canchas["Fútbol"][1]
        inicio = timezone.make_aware(datetime.combine(self.hoy + timedelta(days=10), time(0)))
        BloqueoCancha.objects.create(cancha=auxiliar, fecha_inicio=inicio, fecha_fin=inicio + timedelta(days=1), tipo=BloqueoCancha.Tipo.MANTENIMIENTO,
                                     motivo="Mantenimiento y nivelación del césped sintético", creado_por=self.admin)

    # ── 4. Equipos y plantillas ───────────────────────────────────────────────

    def _nombre_jugador(self, genero):
        nombres = D.NOMBRES_F if genero == "DAMAS" else D.NOMBRES_M
        return self.rng.choice(nombres), f"{self.rng.choice(D.APELLIDOS)} {self.rng.choice(D.APELLIDOS)}"

    def _plantilla(self, equipo, deporte, genero, tamano):
        posiciones = D.POSICIONES[deporte]
        numeros = list(range(2, 31))          # el 1 es del portero
        self.rng.shuffle(numeros)
        carnets = set()
        fichas = []
        for i in range(tamano):
            while True:
                carnet = f"{self.rng.randint(6_000_000, 14_999_999)} SC"
                if carnet not in carnets:
                    carnets.add(carnet)
                    break
            nombre, apellido = self._nombre_jugador(genero)
            posicion = posiciones[0] if i == 0 else posiciones[1 + (i - 1) % (len(posiciones) - 1)]
            fichas.append(FichaJugador(equipo=equipo, nombre=nombre, apellido=apellido, carnet=carnet,
                                       registro=f"{self.rng.choice([2019, 2020, 2021, 2022, 2023, 2024, 2025])}{self.rng.randint(10_000, 99_999)}",
                                       posicion=posicion, numero_camiseta=numeros[i - 1] if i else 1))
        FichaJugador.objects.bulk_create(fichas)

    def _equipos(self):
        self.equipos: dict[str, dict[str, Equipo]] = {}
        for clave, deporte, genero, siglas, sufijo, tamano in D.CATEGORIAS_EQUIPOS:
            self.equipos[clave] = {}
            for sigla in siglas:
                f = self.info[sigla]
                equipo = Equipo.objects.create(nombre=f"{f['apodo']} {sufijo}", facultad=self.facultades[sigla], delegado=self.delegados[sigla], color=f["color"])
                self._plantilla(equipo, deporte, genero, tamano)
                self.equipos[clave][sigla] = equipo

    # ── 5. Campeonatos ────────────────────────────────────────────────────────

    def _campeonato(self, nombre, deporte, genero, estado, formato, inicio, fin, descripcion, **extra):
        minimo, maximo = {"Fútbol": (11, 25), "Futsal": (5, 14), "Voleibol": (6, 12), "Baloncesto": (5, 12)}[deporte]
        return Campeonato.objects.create(nombre=nombre, categoria=self.categorias[(deporte, genero)], estado=estado, formato=formato,
                                         fecha_inicio=inicio, fecha_fin=fin, max_equipos=extra.pop("max_equipos", 12), min_jugadores=minimo,
                                         max_jugadores=maximo, descripcion=descripcion, creado_por=self.organizador, **extra)

    def _inscribir(self, campeonato, equipos, estado=Inscripcion.Estado.APROBADA, observaciones=""):
        for e in equipos:
            Inscripcion.objects.create(campeonato=campeonato, equipo=e, estado=estado, observaciones=observaciones,
                                       validado_por=self.admin if estado != Inscripcion.Estado.PENDIENTE else None,
                                       fecha_validacion=timezone.now() if estado != Inscripcion.Estado.PENDIENTE else None)

    def _goleadores(self, equipo, deporte):
        fichas = list(equipo.jugadores.all())
        return fichas, [D.PESO_GOL.get(f.posicion, 0.5) for f in fichas]

    def _partido_historico(self, campeonato, local, visitante, cuando, cancha, jornada, goles, extra_cards=True):
        """Partido ya jugado con goles y tarjetas repartidos entre los jugadores. Devuelve las incidencias creadas."""
        p = Partido.objects.create(campeonato=campeonato, equipo_local=local, equipo_visitante=visitante, cancha=cancha, fecha_hora=cuando,
                                   jornada=jornada, fase="Liga", duracion_min=90, estado=Partido.Estado.FINALIZADO)
        Resultado.objects.create(partido=p, goles_local=goles[0], goles_visitante=goles[1], registrado_por=self.organizador, verificado=True)
        incidencias = self._incidencias(p, local, visitante, goles, extra_cards)
        Incidencia.objects.bulk_create(incidencias)
        return p

    def _incidencias(self, partido, local, visitante, goles, tarjetas=True):
        deporte = partido.campeonato.categoria.deporte.nombre
        lista = []
        for equipo, cantidad in ((local, goles[0]), (visitante, goles[1])):
            fichas, pesos = self._goleadores(equipo, deporte)
            for minuto in sorted(self.rng.randint(1, 89) for _ in range(cantidad)):
                lista.append(Incidencia(partido=partido, tipo=T.GOL, jugador=self.rng.choices(fichas, pesos)[0], minuto=minuto, registrado_por=self.organizador))
        if tarjetas:
            for equipo in (local, visitante):
                fichas = list(equipo.jugadores.all())
                for _ in range(poisson(self.rng, 1.1)):
                    lista.append(Incidencia(partido=partido, tipo=T.TARJETA_AMARILLA, jugador=self.rng.choice(fichas), minuto=self.rng.randint(8, 88), registrado_por=self.organizador))
                if self.rng.random() < 0.05:
                    lista.append(Incidencia(partido=partido, tipo=T.TARJETA_ROJA, jugador=self.rng.choice(fichas), minuto=self.rng.randint(30, 89), registrado_por=self.organizador))
        return lista

    def _marcador(self, local, visitante, sigla_l, sigla_v, base):
        fl, fv = self.info[sigla_l]["fuerza"], self.info[sigla_v]["fuerza"]
        tope = round(base * 4)                   # ningún equipo anota una cifra absurda: las goleadas históricas se agregan a mano
        return (min(tope, poisson(self.rng, base * math.exp(0.32 * (fl - fv) + 0.08))),
                min(tope, poisson(self.rng, base * math.exp(0.32 * (fv - fl) - 0.04))))

    def _liga_historica(self, nombre, deporte, clave, inicio, fin, base_goles, hora, dia_extra, descripcion, anomalia=False):
        campeonato = self._campeonato(nombre, deporte, "VARONES", Campeonato.Estado.FINALIZADO, Campeonato.Formato.LIGA, inicio, fin, descripcion,
                                      max_equipos=len(self.equipos[clave]))
        por_sigla = self.equipos[clave]
        self._inscribir(campeonato, por_sigla.values())
        inverso = {e.pk: s for s, e in por_sigla.items()}
        canchas = self.canchas[deporte]
        for numero, jornada in enumerate(_round_robin(list(por_sigla.values())), start=1):
            dia = inicio + timedelta(days=7 * (numero - 1) + dia_extra)
            for k, (local, visitante) in enumerate(jornada):
                cancha = canchas[k % len(canchas)]
                inicio_slot = datetime.combine(dia, time(hora)) + timedelta(minutes=105 * (k // len(canchas)))
                goles = self._marcador(local, visitante, inverso[local.pk], inverso[visitante.pk], base_goles)
                if anomalia and numero == 6 and k == 0:
                    goles = (9, 0)                      # una goleada histórica poco común: la IA la señalará para revisión
                self._partido_historico(campeonato, local, visitante, timezone.make_aware(inicio_slot), cancha, numero, goles)
        tabla.recalcular(campeonato)
        return campeonato

    def _temporadas_2025(self):
        self.stdout.write("Creando la temporada 2025 (Fútbol y Futsal)...")
        self.futbol_2025 = self._liga_historica(
            "Interfacultades de Fútbol Varones 2025", "Fútbol", "futbol_v", date(2025, 3, 8), date(2025, 6, 7), 1.15, 8, 0,
            "Torneo anual de fútbol entre las facultades de la UAGRM. Temporada 2025 finalizada.", anomalia=True)
        self.futsal_2025 = self._liga_historica(
            "Interfacultades de Futsal Varones 2025", "Futsal", "futsal_v", date(2025, 8, 3), date(2025, 9, 28), 3.1, 15, 0,
            "Torneo anual de futsal entre las facultades de la UAGRM. Temporada 2025 finalizada.")

    # ── 6. Temporada en curso (generada por el propio sistema) ─────────────────

    def _temporada_en_curso(self):
        self.stdout.write("Generando el fixture de la temporada 2026 con el optimizador del sistema...")
        inicio = self.hoy - timedelta(days=21)
        c = self._campeonato("Interfacultades de Fútbol Varones 2026", "Fútbol", "VARONES", Campeonato.Estado.INSCRIPCION_CERRADA,
                             Campeonato.Formato.LIGA, inicio, inicio + timedelta(days=77),
                             "Torneo anual de fútbol entre las facultades de la UAGRM. Temporada 2026 en curso: todos contra todos a una vuelta.")
        self._inscribir(c, self.equipos["futbol_v"].values())
        generador = FixtureGenerator(c.pk, hora_inicio="15:00", dias_entre_jornadas=7)
        generador.generar(usar_ml=True)
        Campeonato.objects.filter(pk=c.pk).update(estado=Campeonato.Estado.EN_CURSO)
        c.refresh_from_db()
        self.futbol_2026 = c
        inverso = {e.pk: s for s, e in self.equipos["futbol_v"].items()}
        jugados = Partido.objects.filter(campeonato=c, jornada__lte=3).select_related("equipo_local", "equipo_visitante").order_by("fecha_hora", "pk")
        ultimo_j3 = list(jugados.filter(jornada=3))[-1]
        for p in jugados:
            goles = self._marcador(p.equipo_local, p.equipo_visitante, inverso[p.equipo_local_id], inverso[p.equipo_visitante_id], 1.15)
            incidencias = self._incidencias(p, p.equipo_local, p.equipo_visitante, goles)
            if p == ultimo_j3 and not any(i.tipo == T.TARJETA_ROJA for i in incidencias):
                # Garantiza un jugador sancionado de ejemplo para probar la regla de suspensión.
                incidencias.append(Incidencia(partido=p, tipo=T.TARJETA_ROJA, jugador=self.rng.choice(list(p.equipo_local.jugadores.all())), minuto=71, registrado_por=self.organizador))
            for inc in incidencias:
                inc.save()
                sanciones.aplicar_sancion(inc)
            resultados.registrar_resultado(p, {"goles_local": goles[0], "goles_visitante": goles[1]}, self.organizador)
        self.jugados_2026 = list(jugados)

    # ── 7. Otros campeonatos ──────────────────────────────────────────────────

    def _otros_campeonatos(self):
        futsal = self.equipos["futsal_v"]
        copa = self._campeonato("Copa Relámpago de Futsal Varones 2026", "Futsal", "VARONES", Campeonato.Estado.INSCRIPCION_CERRADA,
                                Campeonato.Formato.ELIMINACION, self.hoy + timedelta(days=14), self.hoy + timedelta(days=35),
                                "Copa de eliminación directa. Inscripciones cerradas: genera el fixture sembrando con IA para que los mejores no se crucen temprano.",
                                max_equipos=8)
        self._inscribir(copa, futsal.values())
        voley = self.equipos["voley_d"]
        liga_v = self._campeonato("Copa de Voleibol Damas 2026", "Voleibol", "DAMAS", Campeonato.Estado.INSCRIPCIONES, Campeonato.Formato.LIGA,
                                  self.hoy + timedelta(days=20), self.hoy + timedelta(days=60),
                                  "Inscripciones abiertas para el torneo de voleibol femenino.", max_equipos=8,
                                  fecha_cierre_inscripcion=timezone.now() + timedelta(days=9))
        siglas = list(voley)
        self._inscribir(liga_v, [voley[s] for s in siglas[:3]])
        self._inscribir(liga_v, [voley[s] for s in siglas[3:5]], Inscripcion.Estado.PENDIENTE)
        self._inscribir(liga_v, [voley[s] for s in siglas[5:]], Inscripcion.Estado.RECHAZADA, "Plantel incompleto: menos de 6 jugadoras con ficha activa.")
        self._campeonato("Torneo Interfacultades de Baloncesto Varones 2026", "Baloncesto", "VARONES", Campeonato.Estado.PLANIFICACION,
                         Campeonato.Formato.ELIMINACION, self.hoy + timedelta(days=45), self.hoy + timedelta(days=75),
                         "En planificación: pendiente de abrir inscripciones.", max_equipos=8)

    # ── 8. Quejas ─────────────────────────────────────────────────────────────

    def _quejas(self):
        partidos = [p for p in self.jugados_2026 if p.resultado]
        casos = [
            (Queja.Tipo.QUEJA, Queja.Estado.ABIERTA, "El partido comenzó con 25 minutos de retraso y no se avisó a los delegados.", None),
            (Queja.Tipo.APELACION, Queja.Estado.EN_REVISION, "Solicitamos revisar la tarjeta roja del minuto 62: el jugador no participó en la jugada.", None),
            (Queja.Tipo.QUEJA, Queja.Estado.RESUELTA, "La cancha auxiliar no tenía las líneas demarcadas.", "Se coordinó con mantenimiento: la cancha fue demarcada antes de la siguiente jornada."),
            (Queja.Tipo.APELACION, Queja.Estado.RECHAZADA, "Pedimos anular el resultado por una supuesta alineación indebida.", "No se encontró evidencia de alineación indebida: todos los jugadores tenían ficha vigente."),
        ]
        for partido, (tipo, estado, texto, resolucion) in zip(partidos[::3], casos):
            delegado = partido.equipo_local.delegado
            q = Queja.objects.create(tipo=tipo, estado=estado, descripcion=texto, resolucion=resolucion, encuentro=partido, delegado=delegado,
                                     admin_resuelve=self.admin if resolucion else None, resuelta_en=timezone.now() if resolucion else None)
            q.fecha_hora = timezone.now() - timedelta(days=self.rng.randint(1, 12))
            q.save(update_fields=["fecha_hora"])

    # ── 9. Jugadores con cuenta ───────────────────────────────────────────────

    def _jugadores_con_cuenta(self):
        elegidos = []
        sancionado = FichaJugador.objects.filter(partidos_sancion_restantes__gt=0, equipo__in=self.equipos["futbol_v"].values()).first()
        goleador = (FichaJugador.objects.filter(equipo=self.equipos["futbol_v"]["FICCT"], incidencias__tipo=T.GOL).distinct().first()
                    or FichaJugador.objects.filter(equipo=self.equipos["futbol_v"]["FICCT"]).first())
        medico = FichaJugador.objects.filter(equipo=self.equipos["futbol_v"]["FCSH"]).order_by("numero_camiseta").first()
        for ficha, correo, etiqueta in ((goleador, "jugador@uagrm.edu.bo", "Jugador (Sistemas FC)"),
                                        (medico, "jugador.medicina@uagrm.edu.bo", "Jugador (Medicina FC)"),
                                        (sancionado, "jugador.sancionado@uagrm.edu.bo", "Jugador sancionado")):
            if ficha is None or ficha in elegidos:
                continue
            cuenta = self._usuario(correo, ficha.nombre, ficha.apellido, Usuario.Rol.JUGADOR, facultad=ficha.equipo.facultad, etiqueta=etiqueta)
            FichaJugador.objects.filter(pk=ficha.pk).update(usuario=cuenta)
            elegidos.append(ficha)

    # ── 10. Bitácora ──────────────────────────────────────────────────────────

    def _bitacora(self):
        A = Bitacora.Accion
        for accion, usuario, modulo, texto in [
            (A.CREAR, self.admin, "campeonato", "Campeonato «Interfacultades de Fútbol Varones 2026» creado."),
            (A.GENERAR_FIXTURE, self.organizador, "campeonato", "Fixture generado con el optimizador de ML (66 partidos)."),
            (A.CAMBIO_ESTADO, self.organizador, "campeonato", "Campeonato iniciado y publicado."),
            (A.REGISTRAR_RESULTADO, self.organizador, "partido", "Resultados de las jornadas 1 a 3 registrados."),
            (A.CAMBIO_ESTADO, self.admin, "campeonato", "Inscripciones de la Copa de Voleibol Damas abiertas."),
            (A.EDITAR, self.admin, "inscripcion", "Inscripción rechazada: plantel incompleto."),
            (A.CREAR, self.admin, "usuario", "Cuentas de delegados creadas para las 12 facultades."),
        ]:
            registrar(accion, usuario=usuario, modulo=modulo, descripcion=texto)

    # ── 11. IA ────────────────────────────────────────────────────────────────

    def _entrenar_modelos(self):
        from apps.ml.services import atipicos, predictor
        self.stdout.write("Entrenando los modelos (predictor de resultados y puntuador del fixture)...")
        informe = predictor.entrenar()
        call_command("entrenar_asignacion", "--historial", verbosity=0)
        self.alertas = len(atipicos.escanear())
        self._pronostico()
        self.stdout.write(f"  Predictor: {'entrenado' if informe.get('entrenado') else 'sin entrenar'}"
                          f"{' y activo' if informe.get('activo') else ''}; alertas de resultados atípicos: {self.alertas}.")

    def _pronostico(self):
        """Guarda el pronóstico real (Open-Meteo) de los partidos de los próximos 3 días, sin enviar avisos. Si no hay red, se omite."""
        from apps.ml.services.clima import ServicioClima
        servicio, ahora = ServicioClima(), timezone.now()
        proximos = Partido.objects.filter(estado=Partido.Estado.PROGRAMADO, fecha_hora__gte=ahora, fecha_hora__lte=ahora + timedelta(days=3)).select_related("cancha")
        try:
            for partido in proximos:
                servicio.consultar(partido, persistir=True)
        except Exception:  # noqa: BLE001 - sin internet el seed sigue; el clima se consulta luego desde la planilla del partido
            self.stdout.write("  Pronóstico del clima: sin conexión, se omite.")

    def _resumen(self):
        from apps.fixture.models import Partido as P
        self.stdout.write(self.style.SUCCESS("\nDatos de ejemplo creados."))
        self.stdout.write(f"  Facultades {Facultad.objects.count()} · equipos {Equipo.objects.count()} · jugadores {FichaJugador.objects.count()} · "
                          f"campeonatos {Campeonato.objects.count()} · partidos {P.objects.count()} "
                          f"({P.objects.filter(estado='FINALIZADO').count()} jugados)")
        self.stdout.write(f"  Contraseña de todas las cuentas de ejemplo: {self.password}")
        for etiqueta, correo, nombre in self.credenciales:
            self.stdout.write(f"  {etiqueta:<24} {correo:<40} {nombre}")
