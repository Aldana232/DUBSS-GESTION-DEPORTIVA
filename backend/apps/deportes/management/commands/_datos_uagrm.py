"""Datos de ejemplo para `seed_realista`: facultades de la UAGRM, nombres bolivianos e instalaciones."""

# (sigla, nombre, apodo del equipo, color, fuerza deportiva relativa, delegado (nombre, apellido))
FACULTADES = [
    ("FICCT", "Facultad de Ingeniería en Ciencias de la Computación y Telecomunicaciones", "Sistemas", "#1d4ed8", 1.2, ("Alejandro", "Peña Guzmán")),
    ("FCEAF", "Facultad de Ciencias Económicas, Administrativas y Financieras", "Economía", "#0f766e", 1.0, ("Andrea", "Cuéllar Hurtado")),
    ("FPOLI", "Facultad Politécnica", "Politécnica", "#b45309", 0.8, ("Fabiola", "Durán Terrazas")),
    ("FCET", "Facultad de Ciencias Exactas y Tecnología", "Exactas", "#6d28d9", 0.6, ("Jorge Luis", "Chávez Pinto")),
    ("FCSH", "Facultad de Ciencias de la Salud Humana", "Medicina", "#be123c", 0.3, ("Daniela", "Vaca Parada")),
    ("FAUD", "Facultad de Arquitectura, Urbanismo y Diseño", "Arquitectura", "#0e7490", 0.1, ("Rodrigo", "Villarroel Añez")),
    ("FCJPSRI", "Facultad de Ciencias Jurídicas, Políticas, Sociales y de Relaciones Internacionales", "Derecho", "#374151", -0.1, ("Gonzalo", "Egüez Ribera")),
    ("FH", "Facultad de Humanidades", "Humanidades", "#c2410c", -0.3, ("Verónica", "Salvatierra Moreno")),
    ("FOD", "Facultad de Odontología", "Odontología", "#0369a1", -0.5, ("Mauricio", "Soliz Antelo")),
    ("FCA", "Facultad de Ciencias Agrícolas", "Agronomía", "#15803d", -0.7, ("Marcelo", "Antelo Suárez")),
    ("FCV", "Facultad de Ciencias Veterinarias", "Veterinaria", "#a16207", -0.9, ("Wilson", "Justiniano Arias")),
    ("FCFB", "Facultad de Ciencias Farmacéuticas y Bioquímicas", "Farmacia", "#7e22ce", -1.1, ("Patricia", "Roca Montaño")),
]

DEPORTES = [
    ("Fútbol", 11, "Fútbol de campo, once jugadores por equipo."),
    ("Futsal", 5, "Fútbol de salón en cancha cubierta, cinco jugadores por equipo."),
    ("Voleibol", 6, "Voleibol de sala, seis jugadores por equipo."),
    ("Baloncesto", 5, "Baloncesto, cinco jugadores por equipo."),
]

# (clave, deporte, género, siglas de facultades con equipo, sufijo del nombre, jugadores por plantel)
CATEGORIAS_EQUIPOS = [
    ("futbol_v", "Fútbol", "VARONES", ["FICCT", "FCEAF", "FPOLI", "FCET", "FCSH", "FAUD", "FCJPSRI", "FH", "FOD", "FCA", "FCV", "FCFB"], "FC", 17),
    ("futsal_v", "Futsal", "VARONES", ["FICCT", "FCEAF", "FPOLI", "FCET", "FCSH", "FAUD", "FCJPSRI", "FOD"], "Futsal", 10),
    ("futbol_d", "Fútbol", "DAMAS", ["FICCT", "FCSH", "FCFB", "FH", "FCJPSRI", "FCEAF"], "FC Damas", 16),
    ("futsal_d", "Futsal", "DAMAS", ["FCSH", "FCFB", "FH", "FCEAF", "FAUD", "FCJPSRI"], "Futsal Damas", 10),
    ("voley_d", "Voleibol", "DAMAS", ["FCSH", "FCFB", "FH", "FOD", "FCEAF", "FCV"], "Voley", 10),
    ("basquet_v", "Baloncesto", "VARONES", ["FICCT", "FPOLI", "FCET", "FCEAF", "FCJPSRI", "FAUD"], "Básquet", 10),
]

POSICIONES = {
    "Fútbol": ["Portero", "Defensa", "Defensa", "Defensa", "Mediocampista", "Mediocampista", "Mediocampista", "Delantero", "Delantero"],
    "Futsal": ["Arquero", "Cierre", "Ala", "Ala", "Pívot"],
    "Voleibol": ["Armadora", "Central", "Opuesta", "Líbero", "Punta", "Punta"],
    "Baloncesto": ["Base", "Escolta", "Alero", "Ala-pívot", "Pívot"],
}
# Peso de cada posición para repartir los goles.
PESO_GOL = {"Portero": 0.02, "Arquero": 0.03, "Defensa": 0.6, "Cierre": 0.7, "Mediocampista": 2.0, "Ala": 2.2, "Delantero": 4.0, "Pívot": 3.0}

NOMBRES_M = ["Juan Carlos", "Luis Fernando", "José Miguel", "Diego", "Marco Antonio", "Carlos", "Andrés", "Daniel", "Sebastián", "Rodrigo",
             "Gustavo", "Pablo", "Mauricio", "Fabricio", "Nelson", "Rolando", "Alvaro", "Cristian", "Jhoel", "Brayan", "Edson", "Leonardo",
             "Miguel Ángel", "Iván", "Joaquín", "Mateo", "Santiago", "Adrián", "Ronald", "Oscar", "Limbert", "Kevin"]
NOMBRES_F = ["María José", "Ana Lucía", "Carla", "Daniela", "Fernanda", "Gabriela", "Valeria", "Camila", "Andrea", "Paola", "Jimena",
             "Rocío", "Sofía", "Mariana", "Alejandra", "Lorena", "Katherine", "Noelia", "Brenda", "Yesica", "Milenka", "Ximena",
             "Isabela", "Natalia", "Karen", "Melissa", "Stefany", "Rosario", "Lucía", "Abigail"]
APELLIDOS = ["Mamani", "Quispe", "Flores", "Rojas", "Vargas", "Gutiérrez", "Suárez", "Justiniano", "Parada", "Roca", "Soliz", "Durán",
             "Cuéllar", "Egüez", "Salvatierra", "Añez", "Chávez", "Peña", "Rivero", "Montaño", "Ribera", "Arias", "Moreno", "Villarroel",
             "Terrazas", "Antelo", "Hurtado", "Pinto", "Guzmán", "Ortiz", "Cuéllar", "Zeballos", "Vaca", "Méndez", "Camacho", "Ayala",
             "Paz", "Barba", "Lijerón", "Saucedo", "Banzer", "Heredia", "Carrasco", "Choque", "Condori", "Mercado", "Oviedo", "Padilla"]

INSTALACIONES = [
    {
        "nombre": "Complejo Deportivo Universitario", "tipo": "Complejo deportivo", "capacidad": 2500,
        "ubicacion": "Ciudad Universitaria Gabriel René Moreno, Av. Busch, Santa Cruz de la Sierra",
        "canchas": [
            ("Cancha de Fútbol Principal", "Fútbol", "CESPED_NATURAL", 1500, False),
            ("Cancha de Fútbol Auxiliar", "Fútbol", "CESPED_SINTETICO", 500, False),
        ],
    },
    {
        "nombre": "Coliseo Cerrado Universitario", "tipo": "Coliseo cubierto", "capacidad": 1200,
        "ubicacion": "Ciudad Universitaria Gabriel René Moreno, Av. Busch, Santa Cruz de la Sierra",
        "canchas": [
            ("Cancha Techada A", "Futsal", "PARQUET", 800, True),
            ("Cancha Techada B", "Futsal", "PARQUET", 400, True),
            ("Cancha de Voleibol", "Voleibol", "PARQUET", 500, True),
            ("Cancha de Baloncesto", "Baloncesto", "PARQUET", 600, True),
        ],
    },
    {
        "nombre": "Polideportivo Facultad Politécnica", "tipo": "Polideportivo", "capacidad": 600,
        "ubicacion": "Campus de la Facultad Politécnica, Santa Cruz de la Sierra",
        "canchas": [("Cancha de Futsal al Aire Libre", "Futsal", "CEMENTO", 300, False)],
    },
]

# (sigla, día de la semana 0=lunes, desde, hasta, motivo): clases y prácticas que impiden jugar.
RESTRICCIONES = [
    ("FCSH", 1, (14, 0), (17, 0), "Prácticas hospitalarias"),
    ("FCSH", 3, (14, 0), (17, 0), "Prácticas hospitalarias"),
    ("FCV", 0, (14, 0), (16, 0), "Prácticas de campo en la granja"),
    ("FOD", 2, (15, 0), (18, 0), "Atención en la clínica odontológica"),
    ("FICCT", 4, (14, 0), (16, 0), "Laboratorios de redes"),
]
