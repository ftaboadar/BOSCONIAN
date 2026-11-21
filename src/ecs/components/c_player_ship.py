import pygame


class CPlayerShip:
    """Datos de la nave: avanza sola hacia `heading` y acelera hasta `max_speed`."""

    def __init__(self, heading: tuple[int, int], max_speed: float, acceleration: float) -> None:
        self.heading = heading  # una de las 8 direcciones, como (dx, dy) enteros
        self.speed = 0.0
        self.max_speed = max_speed
        self.acceleration = acceleration
        self.held: set[str] = set()  # acciones de dirección que están presionadas


class CHeadingSprites:
    """Un sprite por cada una de las 8 direcciones, indexado por (dx, dy)."""

    def __init__(self, surfaces: dict[tuple[int, int], pygame.Surface]) -> None:
        self.surfaces = surfaces
