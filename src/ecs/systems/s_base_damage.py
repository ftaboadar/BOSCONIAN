"""Daño a las bases: se destruyen al perder las seis torretas o con un disparo al núcleo."""

import esper
import pygame

from src.ecs.components.c_base import CBase
from src.ecs.components.c_base_core import CBaseCore
from src.ecs.components.c_base_part import CBasePart
from src.ecs.components.c_destroy import CDestroy
from src.ecs.components.c_points import CPoints
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_turret import CTurret
from src.ecs.systems.s_alert import alert_base_destroyed


def damage_base_part(world: esper.World, part: int, shot_dir: pygame.Vector2) -> int:
    """Aplica un disparo que viaja en `shot_dir` a una torreta o al núcleo de una base
    y devuelve los puntos ganados.

    Una torreta siempre se destruye; al caer la sexta cae la base entera. El núcleo solo
    es vulnerable a disparos en la dirección de la orientación de la base o en diagonal
    (un único disparo la destruye); en la dirección perpendicular, o si está cerrado, no
    le pasa nada. Lo destruido queda marcado con CDestroy: explota y suena con
    system_explode y lo borra system_destroy. Una parte ya destruida (dos balas en el
    mismo frame) no da puntos.
    """
    if not world.entity_exists(part) or world.has_component(part, CDestroy):
        return 0
    c_part = world.component_for_entity(part, CBasePart)
    base = c_part.base
    c_base = world.component_for_entity(base, CBase)
    if c_part.kind == "core":
        c_core = world.try_component(part, CBaseCore)
        if c_core is not None and c_core.frame == 0:
            return 0  # cerrado: el disparo no entra
        along = abs(shot_dir.y) if c_base.orientation == "vertical" else abs(shot_dir.x)
        across = abs(shot_dir.x) if c_base.orientation == "vertical" else abs(shot_dir.y)
        return _destroy_base(world, base) if along > 0 and along >= across else 0
    points = world.component_for_entity(part, CPoints).points
    surf = world.component_for_entity(base, CSurface).surf
    # Si estaba abierta se repone cerrada antes: sus restos no deben conservar ese cuadro.
    draw_turret(surf, c_part.offset, world.component_for_entity(part, CTurret).frames, 0)
    draw_base_part(surf, c_part.offset, c_base.turret_wreck, c_base.turret_radius)
    world.add_component(part, CDestroy())
    standing = [ent for ent in _parts_of(world, base)
                if world.has_component(ent, CTurret) and not world.has_component(ent, CDestroy)]
    if not standing:
        points += _destroy_base(world, base)
    return points


def _parts_of(world: esper.World, base: int) -> list[int]:
    return [ent for ent, c_p in world.get_component(CBasePart) if c_p.base == base]


def draw_base_part(surf: pygame.Surface, offset: pygame.Vector2, sprite: pygame.Surface,
                   radius: int) -> None:
    """Cambia en el sprite de la base la parte que está en `offset` (torreta o núcleo,
    de `radius` px) por `sprite`."""
    center = pygame.Vector2(surf.get_rect().center) + offset
    pygame.draw.circle(surf, (0, 0, 0, 0), center, radius)
    surf.blit(sprite, sprite.get_rect(center=center))


def draw_turret(surf: pygame.Surface, offset: pygame.Vector2, frames: list[pygame.Surface],
                frame: int) -> None:
    """Repone en el sprite de la base la torreta cerrada (`frames[0]`, un recorte exacto
    de ese sprite) y le dibuja encima el cuadro `frame`."""
    rect = frames[0].get_rect(center=pygame.Vector2(surf.get_rect().center) + offset)
    surf.fill((0, 0, 0, 0), rect)
    surf.blit(frames[0], rect)
    if frame:
        surf.blit(frames[frame], rect)


def _destroy_base(world: esper.World, base: int) -> int:
    """Marca para destruir la base, que explota, y sus partes, que desaparecen con ella
    (la torreta que acaba de caer conserva su propia explosión). Devuelve los puntos de la base."""
    world.add_component(base, CDestroy())
    for ent in _parts_of(world, base):
        if not world.has_component(ent, CDestroy):
            world.add_component(ent, CDestroy(explodes=False))
    return world.component_for_entity(base, CPoints).points


def system_bases_destroyed(world: esper.World) -> list[int]:
    """Bases que caen en este frame: devuelve su índice en el nivel, para que la partida
    recuerde que no vuelven. Si quedan otras en pie, la alerta baja un rato a VERDE (con la
    última el nivel termina). Debe correr antes de system_destroy, mientras siguen marcadas."""
    fallen = [c_base.index for _, (c_base, _c_d) in world.get_components(CBase, CDestroy)]
    if fallen and len(world.get_component(CBase)) > len(fallen):
        alert_base_destroyed(world)
    return fallen
