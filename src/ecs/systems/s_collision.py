import esper
import pygame

from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_transform import CTransform


def hitbox_rect(c_t: CTransform, c_hb: CHitBox) -> pygame.FRect:
    """Rectángulo de la hitbox en coordenadas del mundo."""
    return pygame.FRect(c_t.pos + c_hb.offset, c_hb.size)


def _can_collide(hb_a: CHitBox, hb_b: CHitBox) -> bool:
    return hb_b.layer in hb_a.mask or hb_a.layer in hb_b.mask


def system_collision(world: esper.World) -> list[tuple[int, int]]:
    """Detecta colisiones AABB entre hitboxes y devuelve los pares que se tocan.

    No decide qué pasa en cada choque: eso le corresponde a las reglas de colisión.
    """
    boxes = [(ent, c_hb, hitbox_rect(c_t, c_hb))
             for ent, (c_t, c_hb) in world.get_components(CTransform, CHitBox)]
    collisions = []
    for i, (ent_a, hb_a, rect_a) in enumerate(boxes):
        for ent_b, hb_b, rect_b in boxes[i + 1:]:
            if _can_collide(hb_a, hb_b) and rect_a.colliderect(rect_b):
                collisions.append((ent_a, ent_b))
    return collisions
