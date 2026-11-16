import esper
import pygame

from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_transform import CTransform
from src.engine.service_locator import color_from_cfg


def minimap_point(world_pos: pygame.Vector2, world_size: pygame.Vector2, rect: pygame.Rect) -> tuple[int, int]:
    """Coordenada del mundo -> punto del minimapa (el mundo se repite en 2D)."""
    x = (world_pos.x % world_size.x) / world_size.x
    y = (world_pos.y % world_size.y) / world_size.y
    return rect.left + int(x * (rect.width - 1)), rect.top + int(y * (rect.height - 1))


def system_minimap_rendering(world: esper.World, screen: pygame.Surface,
                             cfg: dict, world_size: pygame.Vector2) -> None:
    r = cfg["rect"]
    rect = pygame.Rect(r["x"], r["y"], r["w"], r["h"])
    screen.fill(color_from_cfg(cfg["bg_color"]), rect)
    pygame.draw.rect(screen, color_from_cfg(cfg["border_color"]), rect, 1)
    for _, (c_t, c_m) in world.get_components(CTransform, CMinimapTrack):
        color = color_from_cfg(cfg["dot_colors"][c_m.kind])
        size = 3 if c_m.kind == "base" else 2
        px, py = minimap_point(c_t.pos, world_size, rect)
        screen.fill(color, pygame.Rect(px - size // 2, py - size // 2, size, size))
