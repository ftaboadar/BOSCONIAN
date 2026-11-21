class CLevelClock:
    """Cuentas del nivel: la de BLAST OFF! al empezar y la espera tras morir el jugador."""

    def __init__(self, blast_seconds: float, death_wait: float) -> None:
        self.blast_left = blast_seconds  # segundos de BLAST OFF! que faltan; 0: ya se juega
        self.death_wait = death_wait     # segundos que se ve la explosión de la nave
        self.death_left: float | None = None  # lo que falta de esa espera (None: el jugador vive)
