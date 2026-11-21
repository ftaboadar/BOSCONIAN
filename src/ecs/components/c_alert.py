from enum import Enum, auto


class AlertLevel(Enum):
    GREEN = auto()   # sin enemigos nuevos
    YELLOW = auto()  # salen enemigos según la dificultad del nivel
    RED = auto()     # el nivel tardó demasiado: enemigos más rápidos y más seguidos


class CAlert:
    """Condición de alerta del nivel. Empieza en VERDE, pasa a AMARILLA y, por tiempo, a ROJA."""

    def __init__(self, yellow_after: float, red_after: float, calm_seconds: float,
                 red_speed_factor: float, red_spawn_factor: float) -> None:
        self.level = AlertLevel.GREEN
        self.red_after = red_after        # segundos de nivel jugado hasta la alerta ROJA
        self.calm_seconds = calm_seconds  # segundos en VERDE tras destruir una base
        self.elapsed = 0.0                # segundos de nivel jugado
        self.green_left = yellow_after    # segundos que quedan en VERDE
        self.red_speed_factor = red_speed_factor  # en ROJA los enemigos van tantas veces más rápido
        self.red_spawn_factor = red_spawn_factor  # y salen tantas veces más seguido
