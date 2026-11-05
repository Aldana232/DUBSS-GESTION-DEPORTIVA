"""
config/hashers.py
Argon2 con costo reducido, SOLO para desarrollo local.

Argon2 con los valores por defecto es lento a propósito (unos 2 s por inicio de sesión dentro de Docker en Windows).
En desarrollo se usan parámetros livianos; en producción se mantienen los de `base.py`. Los hashes ya guardados con
los parámetros fuertes siguen siendo válidos y se actualizan solos la próxima vez que esa cuenta inicia sesión.
"""
from django.contrib.auth.hashers import Argon2PasswordHasher


class Argon2Liviano(Argon2PasswordHasher):
    time_cost = 1
    memory_cost = 8192      # KiB
    parallelism = 1
