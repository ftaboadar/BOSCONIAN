class CEnemySpawner:
    """Generador de enemigos del nivel: cada `interval` segundos saca uno, hasta `max_alive`."""

    def __init__(self, interval: float, max_alive: int, difficulty: float) -> None:
        self.interval = interval      # segundos entre enemigos (menor con más dificultad)
        self.max_alive = max_alive    # tope de enemigos vivos a la vez
        self.difficulty = difficulty  # dificultad del nivel (0..1) con la que nacen
        self.timer = 0.0
