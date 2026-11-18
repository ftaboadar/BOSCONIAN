class CBaseCore:
    """Núcleo con ciclo: pasa `closed_seconds` cerrado, se abre, queda `open_seconds`
    abierto y se cierra. Los núcleos siempre abiertos no llevan este componente."""

    def __init__(self, closed_seconds: float, open_seconds: float, frame_seconds: float,
                 frame: int) -> None:
        self.closed_seconds = closed_seconds
        self.open_seconds = open_seconds
        self.frame_seconds = frame_seconds  # duración de cada cuadro intermedio al abrir o cerrar
        self.timer = 0.0
        self.frame = frame  # cuadro dibujado: 0 cerrado ... el último, abierto
