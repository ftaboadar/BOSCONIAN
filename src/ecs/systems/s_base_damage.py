"""Daño a las bases: se destruyen al perder las seis torretas o con un disparo al núcleo."""

import esper
import pygame

from src.ecs.components.c_base import CBase
from src.ecs.components.c_base_part import CBasePart
from src.ecs.components.c_points import CPoints
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform

# Evento de esper: el handler recibe la entidad de la base (ya borrada) y dónde estaba.
BASE_DESTROYED = "base_destroyed"


def damage_base_part(world: esper.World, part: int, shot_dir: pygame.Vector2) -> int:
    """Aplica un disparo que viaja en `shot_dir` a una torreta o al núcleo de una base
    y devuelve los puntos ganados.

    Una torreta siempre se destruye; al caer la sexta cae la base entera. El núcleo solo
    es vulnerable a disparos en la dirección de la orientación de la base o en diagonal
    (un único disparo la destruye); en la dirección perpendicular no le pasa nada. Al destruirse
    la base se emite el evento BASE_DESTROYED. Una parte ya destruida (dos balas en el
    mismo frame) no da puntos.
    """
    if not world.entity_exists(part):
        return 0
    c_part = world.component_for_entity(part, CBasePart)
    base = c_part.base
    c_base = world.component_for_entity(base, CBase)
    if c_part.kind == "core":
        along = abs(shot_dir.y) if c_base.orientation == "vertical" else abs(shot_dir.x)
        across = abs(shot_dir.x) if c_base.orientation == "vertical" else abs(shot_dir.y)
        return _destroy_base(world, base) if along > 0 and along >= across else 0
    points = world.component_for_entity(part, CPoints).points
    _draw_turret_wreck(world, base, c_base, c_part.offset)
    world.delete_entity(part, immediate=True)
    if not _parts_of(world, base, "turret"):
        points += _destroy_base(world, base)
    return points


def _parts_of(world: esper.World, base: int, kind: str | None = None) -> list[int]:
    return [ent for ent, c_p in world.get_component(CBasePart)
            if c_p.base == base and kind in (None, c_p.kind)]


def _draw_turret_wreck(world: esper.World, base: int, c_base: CBase,
                       offset: pygame.Vector2) -> None:
    """Cambia en el sprite de la base la torreta que está en `offset` por sus restos."""
    surf = world.component_for_entity(base, CSurface).surf
    center = pygame.Vector2(surf.get_rect().center) + offset
    pygame.draw.circle(surf, (0, 0, 0, 0), center, c_base.turret_radius)
    surf.blit(c_base.turret_wreck, c_base.turret_wreck.get_rect(center=center))


def _destroy_base(world: esper.World, base: int) -> int:
    """Quita la base con todas sus partes, avisa y devuelve los puntos de la base."""
    points = world.component_for_entity(base, CPoints).points
    pos = pygame.Vector2(world.component_for_entity(base, CTransform).pos)
    for ent in _parts_of(world, base) + [base]:
        world.delete_entity(ent, immediate=True)
    esper.dispatch_event(BASE_DESTROYED, base, pos)
    return points
