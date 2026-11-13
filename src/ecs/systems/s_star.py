import esper
import pygame

from src.ecs.components.c_star import CStar
from src.ecs.components.c_transform import CTransform


def star_alpha(phase: float) -> int:
    """Onda triangular 0 -> 255 -> 0 para una fase de 0 a 1."""
    tri = 1 - abs(2 * (phase % 1.0) - 1)
    return int(255 * tri)


def system_star_blink(world: esper.World, delta_time: float) -> None:
    for _, c_s in world.get_component(CStar):
        c_s.phase = (c_s.phase + c_s.blink_speed * delta_time) % 1.0
        c_s.surf.set_alpha(star_alpha(c_s.phase))


def system_star_movement(world: esper.World, area: pygame.Rect, move: pygame.Vector2) -> None:
    """Mueve las estrellas `move` píxeles dando la vuelta dentro de `area`."""
    for _, (c_t, _c_s) in world.get_components(CTransform, CStar):
        c_t.pos.x = area.left + (c_t.pos.x + move.x - area.left) % area.width
        c_t.pos.y = area.top + (c_t.pos.y + move.y - area.top) % area.height


def system_star_parallax(world: esper.World, area: pygame.Rect,
                         camera_delta: pygame.Vector2, factor: float) -> None:
    """En juego las estrellas se desplazan en sentido contrario a la cámara, más lento."""
    system_star_movement(world, area, -camera_delta * factor)


def system_star_fall(world: esper.World, area: pygame.Rect, speed: float, delta_time: float) -> None:
    """En menús las estrellas caen de arriba hacia abajo."""
    system_star_movement(world, area, pygame.Vector2(0, speed * delta_time))


def system_star_rendering(world: esper.World, screen: pygame.Surface) -> None:
    for _, (c_t, c_s) in world.get_components(CTransform, CStar):
        screen.blit(c_s.surf, (int(c_t.pos.x), int(c_t.pos.y)))
