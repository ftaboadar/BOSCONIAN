"""Funciones que ensamblan entidades a partir de componentes."""

import math
import random

import esper
import pygame

from src.ecs.components.c_camera_target import CCameraTarget
from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_player_ship import CHeadingSprites, CPlayerShip
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


def create_player(world: esper.World, pos: pygame.Vector2, cfg: dict) -> int:
    """Nave del jugador: sprite único hacia arriba, rotado en pasos de 45 grados."""
    r = cfg["sprite_rect"]
    base = ServiceLocator.images.get("ships").subsurface(
        pygame.Rect(r["x"], r["y"], r["w"], r["h"])).copy()
    # Ángulo antihorario de pygame.transform.rotate para cada (dx, dy) con "arriba" = (0, -1).
    sprites = {
        (dx, dy): pygame.transform.rotate(base, round(math.degrees(math.atan2(-dx, -dy))))
        for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)
    }
    heading = (cfg["start_heading"]["x"], cfg["start_heading"]["y"])
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CVelocity(pygame.Vector2()), CSurface(sprites[heading]),
        CWorld(), CCameraTarget(), CMinimapTrack("player"),
        CPlayerShip(heading, cfg["max_speed"], cfg["acceleration"]), CHeadingSprites(sprites),
    )


def create_base_placeholder(world: esper.World, pos: pygame.Vector2) -> int:
    """Base provisional (hito 4 la reemplaza): cuadro rojo de 24x24."""
    surf = pygame.Surface((24, 24))
    surf.fill((200, 40, 40))
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CSurface(surf), CWorld(), CMinimapTrack("base"),
    )
