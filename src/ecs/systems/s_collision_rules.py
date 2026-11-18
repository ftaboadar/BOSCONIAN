import esper
import pygame

from src.ecs.components.c_destroy import CDestroy
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_collision import hitbox_rect


def load_rules(collisions_cfg: dict) -> dict[tuple[str, str], str]:
    """Convierte la lista del JSON en un diccionario (capa_a, capa_b) -> resultado."""
    return {(r["a"], r["b"]): r["result"] for r in collisions_cfg["rules"]}


def system_collision_rules(world: esper.World, collisions: list[tuple[int, int]],
                           rules: dict[tuple[str, str], str]) -> None:
    """Aplica la regla que corresponde a cada par de entidades que chocan.

    BOUNCE: ambas rebotan. BOUNCE_A: solo rebota la entidad de la capa "a"
    (la "b" es fija). DESTROY_BOTH: ambas se marcan con CDestroy.
    """
    for ent_a, ent_b in collisions:
        if not (world.entity_exists(ent_a) and world.entity_exists(ent_b)):
            continue
        layer_a = world.component_for_entity(ent_a, CHitBox).layer
        layer_b = world.component_for_entity(ent_b, CHitBox).layer
        result = rules.get((layer_a, layer_b))
        if result is None:
            result = rules.get((layer_b, layer_a))
            ent_a, ent_b = ent_b, ent_a
        if result is None:
            continue

        if result == "BOUNCE":
            _bounce(world, ent_a, ent_b, move_b=True)
        elif result == "BOUNCE_A":
            _bounce(world, ent_a, ent_b, move_b=False)
        elif result == "DESTROY_BOTH":
            world.add_component(ent_a, CDestroy())
            world.add_component(ent_b, CDestroy())


def _bounce(world: esper.World, ent_a: int, ent_b: int, move_b: bool) -> None:
    """Separa las hitboxes por el eje de menor penetración e invierte la velocidad
    en ese eje si la entidad se movía hacia la otra."""
    t_a = world.component_for_entity(ent_a, CTransform)
    t_b = world.component_for_entity(ent_b, CTransform)
    rect_a = hitbox_rect(t_a, world.component_for_entity(ent_a, CHitBox))
    rect_b = hitbox_rect(t_b, world.component_for_entity(ent_b, CHitBox))

    overlap_x = min(rect_a.right, rect_b.right) - max(rect_a.left, rect_b.left)
    overlap_y = min(rect_a.bottom, rect_b.bottom) - max(rect_a.top, rect_b.top)
    if overlap_x < overlap_y:
        axis = pygame.Vector2(1 if rect_a.centerx >= rect_b.centerx else -1, 0)
        depth = overlap_x
    else:
        axis = pygame.Vector2(0, 1 if rect_a.centery >= rect_b.centery else -1)
        depth = overlap_y

    # axis apunta de b hacia a
    if move_b:
        t_a.pos += axis * (depth / 2)
        t_b.pos -= axis * (depth / 2)
        _reflect(world, ent_b, -axis)
    else:
        t_a.pos += axis * depth
    _reflect(world, ent_a, axis)


def _reflect(world: esper.World, ent: int, away: pygame.Vector2) -> None:
    """Invierte la componente de la velocidad que va en contra de 'away'."""
    c_v = world.try_component(ent, CVelocity)
    if c_v is None:
        return
    if c_v.vel.dot(away) < 0:
        if away.x != 0:
            c_v.vel.x = -c_v.vel.x
        else:
            c_v.vel.y = -c_v.vel.y
