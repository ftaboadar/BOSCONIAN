import pygame


class CTurret:
    """Torreta de una base: cerca del jugador se abre y dispara cada `interval` segundos."""

    def __init__(self, interval: float, frames: list[pygame.Surface]) -> None:
        self.interval = interval  # segundos entre disparos; distinto en cada torreta
        self.frames = frames      # sprites: cerrada, abierta y a punto de disparar
        self.timer = 0.0          # tiempo acumulado con el jugador en su alcance
        self.frame = 0            # índice en `frames` del sprite dibujado
