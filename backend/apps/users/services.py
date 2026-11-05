from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)


def invalidar_tokens_usuario(usuario):
    """Revoca todos los refresh tokens emitidos para un usuario."""
    for token in OutstandingToken.objects.filter(user=usuario):
        BlacklistedToken.objects.get_or_create(token=token)
