"""Funciones que ensamblan entidades a partir de componentes."""

import random

import esper
import pygame

from src.ecs.components.c_camera_target import CCameraTarget
from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_star import CStar
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.c_world import CWorld
from src.engine.service_locator import ServiceLocator, color_from_cfg


def create_image(world: esper.World, image_name: str, center: pygame.Vector2) -> int:
    return world.create_entity(
        CTransform(center),
        CSurface(ServiceLocator.images.get(image_name)),
    )


def create_text(world: esper.World, text: str, color: pygame.Color, center: pygame.Vector2) -> int:
    surf = ServiceLocator.fonts.get("main").render(text, False, color)
    return world.create_entity(CTransform(center), CSurface(surf))


def create_stars(world: esper.World, cfg: dict, area: pygame.Rect) -> None:
    speed = cfg["stars_blink_speed"]  # fija para todas; solo la fase difiere
    for _ in range(cfg["stars_number"]):
        c = random.choice(cfg["star_colors"])
        pos = pygame.Vector2(random.uniform(area.left, area.right - 1),
                             random.uniform(area.top, area.bottom - 1))
        world.create_entity(
            CTransform(pos),
            CStar(color_from_cfg(c),
                  speed,
                  random.random()),
        )


def create_player_placeholder(world: esper.World, pos: pygame.Vector2) -> int:
    """Nave provisional (hito 3 la reemplaza): triángulo blanco de 12x12."""
    surf = pygame.Surface((12, 12), pygame.SRCALPHA)
    pygame.draw.polygon(surf, (255, 255, 255), [(6, 0), (12, 12), (0, 12)])
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CVelocity(pygame.Vector2()), CSurface(surf),
        CWorld(), CCameraTarget(), CMinimapTrack("player"),
    )


def create_base_placeholder(world: esper.World, pos: pygame.Vector2) -> int:
    """Base provisional (hito 4 la reemplaza): cuadro rojo de 24x24."""
    surf = pygame.Surface((24, 24))
    surf.fill((200, 40, 40))
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CSurface(surf), CWorld(), CMinimapTrack("base"),
    )
