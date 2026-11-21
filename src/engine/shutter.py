"""Persiana entre pantallas, como la del Bosconian original: dos bandas verde menta se cierran
desde arriba y desde abajo sobre el campo de juego, se cambia de escena con el campo cubierto y
se abren de nuevo. La barra lateral queda fuera: el motor la dibuja después."""

import pygame

from src.engine.data_loader import ConfigError, require_keys
from src.engine.service_locator import color_from_cfg

IDLE, CLOSING, CLOSED, OPENING = "idle", "closing", "closed", "opening"


class Shutter:
    def __init__(self, cfg: dict, stage: pygame.Rect) -> None:
        require_keys(cfg, ("close_seconds", "open_seconds", "color", "to"), "world.json shutter")
        if cfg["close_seconds"] <= 0 or cfg["open_seconds"] <= 0:
            raise ConfigError("world.json shutter: close_seconds y open_seconds deben ser mayores que 0")
        self.close_seconds = cfg["close_seconds"]
        self.open_seconds = cfg["open_seconds"]
        self.color = color_from_cfg(cfg["color"])
        self.scenes = tuple(cfg["to"])  # escenas a las que se llega con persiana
        self.stage = pygame.Rect(stage)
        self.state = IDLE
        self.target: str | None = None
        self.time = 0.0

    def wants(self, scene: str) -> bool:
        """¿Se llega a esta escena con persiana?"""
        return scene in self.scenes

    @property
    def busy(self) -> bool:
        return self.state != IDLE

    @property
    def closing(self) -> bool:
        return self.state == CLOSING

    def close(self, target: str) -> bool:
        """Empieza a cerrarse para ir a `target`. No hace nada si ya hay una persiana en marcha."""
        if self.busy:
            return False
        self.state, self.target, self.time = CLOSING, target, 0.0
        return True

    def open(self) -> None:
        """Con el campo cubierto y la escena ya cambiada, empieza a abrirse."""
        self.state, self.time = OPENING, 0.0

    def update(self, delta_time: float) -> bool:
        """Avanza la persiana. Devuelve True en el fotograma en que el campo queda cubierto."""
        if self.state == CLOSING:
            self.time += delta_time
            if self.time >= self.close_seconds:
                self.state = CLOSED
                return True
        elif self.state == OPENING:
            self.time += delta_time
            if self.time >= self.open_seconds:
                self.state, self.target = IDLE, None
        return False

    @property
    def cover(self) -> float:
        """Cuánto del campo cubren las bandas: 0 abierta, 1 cerrada del todo."""
        if self.state == CLOSING:
            return min(self.time / self.close_seconds, 1.0)
        if self.state == CLOSED:
            return 1.0
        if self.state == OPENING:
            return 1.0 - min(self.time / self.open_seconds, 1.0)
        return 0.0

    def draw(self, screen: pygame.Surface) -> None:
        cover = self.cover
        if cover <= 0:
            return
        band = round(self.stage.h / 2 * cover)  # alto de cada banda
        screen.fill(self.color, pygame.Rect(self.stage.left, self.stage.top, self.stage.w, band))
        screen.fill(self.color, pygame.Rect(self.stage.left, self.stage.bottom - band, self.stage.w, band))
