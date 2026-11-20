class CSteering:
    """Parámetros de steering de un enemigo. La rapidez es constante; solo cambia el rumbo."""

    def __init__(self, turn_rate: float, deviation: float = 0.0,
                 wander: dict | None = None) -> None:
        self.turn_rate = turn_rate  # grados por segundo que puede girar
        self.deviation = deviation  # grados que se desvía al perseguir (según dificultad)
        self.wander = wander or {}  # distance, radius y jitter del wander
        self.wander_angle = 0.0     # ángulo actual sobre el círculo del wander
