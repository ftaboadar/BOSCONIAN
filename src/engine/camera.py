"""Cámara sobre un mundo toroidal: sigue un objetivo y convierte coordenadas."""

import pygame


def wrap_delta(delta: pygame.Vector2, world_size: pygame.Vector2) -> pygame.Vector2:
    """Diferencia más corta entre dos puntos de un mundo que se repite."""
    return pygame.Vector2(
        (delta.x + world_size.x / 2) % world_size.x - world_size.x / 2,
        (delta.y + world_size.y / 2) % world_size.y - world_size.y / 2,
    )


class Camera:
    def __init__(self, world_size: pygame.Vector2, viewport: pygame.Rect) -> None:
        self.world_size = world_size
        self.viewport = viewport
        self.pos = pygame.Vector2(world_size.x / 2, world_size.y / 2)
        self.delta = pygame.Vector2()

    def follow(self, target: pygame.Vector2) -> None:
        """Centra la cámara en el objetivo y guarda el desplazamiento del frame."""
        self.delta = wrap_delta(target - self.pos, self.world_size)
        self.pos = pygame.Vector2(target.x % self.world_size.x, target.y % self.world_size.y)

    def world_to_screen(self, world_pos: pygame.Vector2) -> pygame.Vector2:
        offset = wrap_delta(world_pos - self.pos, self.world_size)
        return pygame.Vector2(self.viewport.center) + offset
