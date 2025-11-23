import httpx


# Compatibilidad con httpx>=0.28: eliminar parámetro `app` que TestClient ya no acepta
_orig_client_init = httpx.Client.__init__


def _compat_client_init(self, *args, **kwargs):
    kwargs.pop("app", None)
    return _orig_client_init(self, *args, **kwargs)


httpx.Client.__init__ = _compat_client_init
