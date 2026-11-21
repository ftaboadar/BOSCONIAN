from enum import Enum

import pygame


class ShutterState(Enum):
    IDLE = "idle"
    CLOSING = "closing"
    OPENING = "opening"


class CShutter:
    """Persiana entre pantallas: dos bandas que se cierran sobre el campo de juego (`stage`)
    desde arriba y desde abajo, y se abren de nuevo con la escena `target` ya puesta."""

    def __init__(self, close_seconds: float, open_seconds: float, color: pygame.Color,
                 scenes: tuple[str, ...], stage: pygame.Rect) -> None:
        self.close_seconds = close_seconds
        self.open_seconds = open_seconds
        self.color = color
        self.scenes = scenes  # escenas a las que se llega con persiana
        self.stage = stage
        self.state = ShutterState.IDLE
        self.target: str | None = None
        self.time = 0.0  # segundos que lleva cerrándose o abriéndose
