from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def tipo_required(*tipos):
    """Libera a view só para usuários dos tipos informados (ex.: 'loja')."""
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.user.tipo not in tipos:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator