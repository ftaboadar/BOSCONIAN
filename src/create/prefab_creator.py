"""Funciones que ensamblan entidades a partir de componentes."""

import esper
import pygame

from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.engine.service_locator import ServiceLocator


def create_image(world: esper.World, image_name: str, pos: pygame.Vector2) -> int:
    return world.create_entity(
        CTransform(pos),
        CSurface(ServiceLocator.images.get(image_name)),
    )


def create_text(world: esper.World, text: str, color: pygame.Color, pos: pygame.Vector2) -> int:
    surf = ServiceLocator.fonts.get("main").render(text, False, color)
    return world.create_entity(CTransform(pos), CSurface(surf))
