"""Radar del panel lateral, como el del Bosconian original: un mapa FIJO del mundo entero.

No se mueve con la nave: las bases se ven siempre en su sitio y la nave es un punto que recorre
el mapa. Como el mundo es toroidal, al llegar a un borde el punto sale por el lado opuesto.
El mundo se reparte linealmente por todo el radar (que es más alto que ancho)."""

import esper
import pygame

from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_transform import CTransform
from src.engine.service_locator import color_from_cfg


def radar_rect(cfg: dict) -> pygame.Rect:
    r = cfg["rect"]
    return pygame.Rect(r["x"], r["y"], r["w"], r["h"])


def radar_point(world_pos: pygame.Vector2, world_size: pygame.Vector2,
                rect: pygame.Rect) -> tuple[int, int]:
    """Punto del radar de una posición del mundo. Un punto que se sale del mundo reaparece por
    el lado opuesto (el mundo se repite). La esquina (0, 0) del mundo es la de arriba a la izquierda."""
    x = (world_pos.x % world_size.x) / world_size.x
    y = (world_pos.y % world_size.y) / world_size.y
    return (rect.left + min(int(x * rect.width), rect.width - 1),
            rect.top + min(int(y * rect.height), rect.height - 1))


def system_minimap_rendering(world: esper.World, screen: pygame.Surface, cfg: dict,
                             world_size: pygame.Vector2) -> None:
    rect = radar_rect(cfg)
    screen.fill(color_from_cfg(cfg["bg_color"]), rect)
    for _, (c_t, c_m) in world.get_components(CTransform, CMinimapTrack):
        size = cfg["dot_sizes"][c_m.kind]
        mark = pygame.Rect(0, 0, size, size)
        mark.center = radar_point(c_t.pos, world_size, rect)
        screen.fill(color_from_cfg(cfg["dot_colors"][c_m.kind]), mark.clip(rect))
