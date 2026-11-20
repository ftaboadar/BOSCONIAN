"""Funciones que ensamblan entidades a partir de componentes."""

import random

import esper
import pygame

from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_camera_target import CCameraTarget
from src.ecs.components.c_explosive import CExplosive
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_star import CStar
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.c_world import CWorld
from src.engine.data_loader import load_json
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


def create_hitbox(kind: str) -> CHitBox:
    """Crea la CHitBox de un tipo de entidad según la sección "hitboxes" de collisions.json."""
    cfg = load_json("assets/cfg/collisions.json")["hitboxes"][kind]
    offset = cfg.get("offset", {"x": 0, "y": 0})
    return CHitBox(pygame.Vector2(cfg["size"]["w"], cfg["size"]["h"]),
                   pygame.Vector2(offset["x"], offset["y"]),
                   cfg["layer"], tuple(cfg["mask"]))


def create_player_placeholder(world: esper.World, pos: pygame.Vector2) -> int:
    """Nave provisional (hito 3 la reemplaza): triángulo blanco de 12x12."""
    surf = pygame.Surface((12, 12), pygame.SRCALPHA)
    pygame.draw.polygon(surf, (255, 255, 255), [(6, 0), (12, 12), (0, 12)])
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CVelocity(pygame.Vector2()), CSurface(surf),
        CWorld(), CCameraTarget(), CMinimapTrack("player"),
        create_hitbox("player"), CExplosive("player"),
    )


def create_base_placeholder(world: esper.World, pos: pygame.Vector2) -> int:
    """Base provisional (hito 4 la reemplaza): cuadro rojo de 24x24."""
    surf = pygame.Surface((24, 24))
    surf.fill((200, 40, 40))
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CSurface(surf), CWorld(), CMinimapTrack("base"),
        create_hitbox("base"),
    )


def create_explosion(world: esper.World, pos: pygame.Vector2, vel: pygame.Vector2,
                     cfg: dict) -> int:
    """Explosión animada que conserva la velocidad de la entidad destruida.

    cfg es un tipo de explosions.json (por ejemplo cfg["simple"]). La animación
    no se repite: al terminar, system_animation marca la entidad con CDestroy.
    Si el tipo tiene "hitbox", la explosión mata lo que toque mientras dura.
    """
    sheet = ServiceLocator.images.get(cfg["image"])
    frames = [pygame.Rect(f["x"], f["y"], f["w"], f["h"]) for f in cfg["frames"]]
    ent = world.create_entity(
        CTransform(pygame.Vector2(pos)),
        CVelocity(pygame.Vector2(vel)),
        CSurface(sheet.subsurface(frames[0])),
        CAnimation(sheet, frames, cfg["framerate"], loop=False),
        CWorld(),
    )
    if "hitbox" in cfg:  # explosión letal (por ejemplo, la de las minas)
        world.add_component(ent, create_hitbox(cfg["hitbox"]))
    return ent
