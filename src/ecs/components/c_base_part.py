import pygame


class CBasePart:
    """Parte de una base: una de sus seis torretas (turret), su núcleo (core) o una pieza
    sólida de su cuerpo (body)."""

    def __init__(self, base: int, kind: str, offset: pygame.Vector2) -> None:
        self.base = base      # entidad de la base a la que pertenece
        self.kind = kind
        self.offset = offset  # posición respecto al centro de la base
