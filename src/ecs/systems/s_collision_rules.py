import esper
import pygame

from src.create.prefab_creator import create_score_popup
from src.ecs.components.c_base_part import CBasePart
from src.ecs.components.c_destroy import CDestroy
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_points import CPoints
from src.ecs.components.c_invulnerable import CInvulnerable
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_base_damage import damage_base_part
from src.ecs.systems.s_collision import center_delta, hitbox_center


def load_rules(collisions_cfg: dict) -> dict[tuple[str, str], dict]:
    """Convierte la lista del JSON en un diccionario (capa_a, capa_b) -> regla."""
    return {(r["a"], r["b"]): r for r in collisions_cfg["rules"]}


def system_collision_rules(world: esper.World, collisions: list[tuple[int, int]],
                           rules: dict[tuple[str, str], dict],
                           world_size: pygame.Vector2 | None = None,
                           popup_cfg: dict | None = None) -> int:
    """Aplica la regla que corresponde a cada par de entidades que chocan.

    BOUNCE: ambas rebotan. BOUNCE_A: solo rebota la entidad de la capa "a"
    (la "b" es fija). DESTROY_BOTH: ambas se marcan con CDestroy, salvo las
    entidades con CInvulnerable. DESTROY_A: solo se marca la entidad de la capa "a"
    (con la misma excepción). DAMAGE_BASE: la bala de la capa "a" golpea una torreta o el
    núcleo de una base (capa "b"): daña esa parte según la dirección del disparo, da los
    puntos que corresponda (torreta, o base entera) y la bala se consume.

    Si la regla tiene "score": "a" o "b", esa entidad da sus CPoints al destruirse.
    Devuelve los puntos ganados en el frame (una entidad solo puntúa una vez). Con `popup_cfg`
    aparece además un cartel con los puntos donde se destruyó cada cosa.
    """
    points = 0
    for ent_a, ent_b in collisions:
        if not (world.entity_exists(ent_a) and world.entity_exists(ent_b)):
            continue
        if world.has_component(ent_a, CDestroy) or world.has_component(ent_b, CDestroy):
            continue  # ya destruida en este frame: una bala solo se lleva una cosa
        layer_a = world.component_for_entity(ent_a, CHitBox).layer
        layer_b = world.component_for_entity(ent_b, CHitBox).layer
        rule = rules.get((layer_a, layer_b))
        if rule is None:
            rule = rules.get((layer_b, layer_a))
            ent_a, ent_b = ent_b, ent_a  # ent_a queda siempre en la capa "a" de la regla
        if rule is None:
            continue

        scored = {"a": ent_a, "b": ent_b}.get(rule.get("score"))
        if scored is not None:
            gained = _points_if_new(world, scored)
            points += gained
            if gained and popup_cfg:
                create_score_popup(world, world.component_for_entity(scored, CTransform).pos,
                                   gained, popup_cfg)

        result = rule["result"]
        if result == "BOUNCE":
            _bounce(world, ent_a, ent_b, True, world_size)
        elif result == "BOUNCE_A":
            _bounce(world, ent_a, ent_b, False, world_size)
        elif result == "DESTROY_BOTH":
            _mark_destroy(world, ent_a)
            _mark_destroy(world, ent_b)
        elif result == "DESTROY_A":
            _mark_destroy(world, ent_a)
        elif result == "DAMAGE_BASE":
            shot = world.component_for_entity(ent_a, CVelocity).vel
            part_pos = pygame.Vector2(world.component_for_entity(ent_b, CTransform).pos)
            base_pos = pygame.Vector2(world.component_for_entity(
                world.component_for_entity(ent_b, CBasePart).base, CTransform).pos)
            c_points = world.try_component(ent_b, CPoints)
            part_points = c_points.points if c_points is not None else 0
            gained = damage_base_part(world, ent_b, shot.normalize() if shot.length() else shot)
            points += gained
            if popup_cfg and gained:
                # La torreta y la base suman por separado: se ven como dos carteles.
                if part_points and gained >= part_points:
                    create_score_popup(world, part_pos, part_points, popup_cfg)
                    gained -= part_points
                if gained:
                    create_score_popup(world, base_pos, gained, popup_cfg)
            _mark_destroy(world, ent_a)
    return points


def _points_if_new(world: esper.World, ent: int) -> int:
    """Puntos de la entidad, solo si no estaba ya marcada para destruirse en este frame
    ni es invulnerable (no se destruye, así que no puntúa)."""
    if world.has_component(ent, CDestroy) or world.has_component(ent, CInvulnerable):
        return 0
    c_p = world.try_component(ent, CPoints)
    return c_p.points if c_p is not None else 0


def _mark_destroy(world: esper.World, ent: int) -> None:
    """Marca la entidad con CDestroy, a menos que sea invulnerable."""
    if world.try_component(ent, CInvulnerable) is None:
        world.add_component(ent, CDestroy())


def _bounce(world: esper.World, ent_a: int, ent_b: int, move_b: bool,
            world_size: pygame.Vector2 | None) -> None:
    """Separa las hitboxes por el eje de menor penetración e invierte la velocidad
    en ese eje si la entidad se movía hacia la otra."""
    t_a = world.component_for_entity(ent_a, CTransform)
    t_b = world.component_for_entity(ent_b, CTransform)
    hb_a = world.component_for_entity(ent_a, CHitBox)
    hb_b = world.component_for_entity(ent_b, CHitBox)

    d = center_delta(hitbox_center(t_a, hb_a), hitbox_center(t_b, hb_b), world_size)
    overlap_x = (hb_a.size.x + hb_b.size.x) / 2 - abs(d.x)
    overlap_y = (hb_a.size.y + hb_b.size.y) / 2 - abs(d.y)
    if overlap_x < overlap_y:
        axis = pygame.Vector2(1 if d.x >= 0 else -1, 0)
        depth = overlap_x
    else:
        axis = pygame.Vector2(0, 1 if d.y >= 0 else -1)
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
