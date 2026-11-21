import pygame


class CArrival:
    """Movimiento con destino: quedan `remaining` segundos para llegar a `target`, donde se detiene."""

    def __init__(self, remaining: float, target: pygame.Vector2) -> None:
        self.remaining = remaining
        self.target = pygame.Vector2(target)
