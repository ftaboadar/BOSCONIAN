"""Radar del panel lateral: centrado en la nave, a escala, con el mundo toroidal.

La nave está siempre en el centro (parpadeando) y las demás marcas se ven donde quedan
respecto a ella, tomando el camino más corto: un objeto al otro lado del borde del mundo
aparece cerca. Lo que queda fuera del alcance del radar no se dibuja."""

import esper
import pygame

from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_transform import CTransform
from src.engine.camera import wrap_delta
from src.engine.service_locator import color_from_cfg


def radar_rect(cfg: dict) -> pygame.Rect:
    r = cfg["rect"]
    return pygame.Rect(r["x"], r["y"], r["w"], r["h"])


def radar_point(world_pos: pygame.Vector2, center: pygame.Vector2, world_size: pygame.Vector2,
                rect: pygame.Rect, scale: float) -> tuple[int, int] | None:
    """Punto del radar de una posición del mundo, o None si queda fuera del alcance.

    `center` es lo que está en el centro del radar (la nave); `scale` son píxeles del mundo
    por píxel del radar. El borde del marco no cuenta como alcance."""
    delta = wrap_delta(pygame.Vector2(world_pos) - center, world_size)
    point = (rect.centerx + round(delta.x / scale), rect.centery + round(delta.y / scale))
    return point if rect.inflate(-2, -2).collidepoint(point) else None


def blink_on(elapsed: float, cfg: dict) -> bool:
    """La marca de la nave parpadea: visible la mitad del tiempo."""
    period = cfg["blink_seconds"]
    return elapsed % (2 * period) < period


def system_minimap_rendering(world: esper.World, screen: pygame.Surface, cfg: dict,
                             world_size: pygame.Vector2, center: pygame.Vector2,
                             elapsed: float = 0.0) -> None:
    rect = radar_rect(cfg)
    screen.fill(color_from_cfg(cfg["bg_color"]), rect)
    if "border_color" in cfg:  # el del original no tiene marco
        pygame.draw.rect(screen, color_from_cfg(cfg["border_color"]), rect, 1)
    shown = blink_on(elapsed, cfg)
    for _, (c_t, c_m) in world.get_components(CTransform, CMinimapTrack):
        if c_m.kind == "player" and not shown:
            continue
        point = radar_point(c_t.pos, center, world_size, rect, cfg["scale"])
        if point is None:
            continue
        size = cfg["dot_sizes"][c_m.kind]
        mark = pygame.Rect(0, 0, size, size)
        mark.center = point
        screen.fill(color_from_cfg(cfg["dot_colors"][c_m.kind]), mark.clip(rect.inflate(-2, -2)))
        if c_m.kind == "base" and size >= 5:  # el núcleo de la base, de otro color
            screen.set_at(point, color_from_cfg(cfg["base_core_color"]))
