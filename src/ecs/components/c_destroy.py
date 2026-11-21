class CDestroy:
    """Marca una entidad para eliminarla al final del frame.

    Con `explodes` en False desaparece sin explotar aunque sea explosiva: es lo que salió de
    la pantalla, se alejó o agotó su tiempo. Lo que se destruye en un choque sí explota."""

    def __init__(self, explodes: bool = True) -> None:
        self.explodes = explodes
