import esper
import pygame

from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_transform import CTransform
from src.engine.camera import wrap_delta


def hitbox_center(c_t: CTransform, c_hb: CHitBox) -> pygame.Vector2:
    return c_t.pos + c_hb.offset


def hitbox_rect(c_t: CTransform, c_hb: CHitBox) -> pygame.FRect:
    """Rectángulo de la hitbox en coordenadas del mundo (útil para dibujarla en debug)."""
    rect = pygame.FRect((0, 0), c_hb.size)
    rect.center = hitbox_center(c_t, c_hb)
    return rect


def center_delta(center_a: pygame.Vector2, center_b: pygame.Vector2,
                 world_size: pygame.Vector2 | None) -> pygame.Vector2:
    """Vector de b hacia a. En un mundo toroidal toma el camino más corto."""
    delta = center_a - center_b
    return wrap_delta(delta, world_size) if world_size is not None else delta


def _can_collide(hb_a: CHitBox, hb_b: CHitBox) -> bool:
    return hb_b.layer in hb_a.mask or hb_a.layer in hb_b.mask


def system_collision(world: esper.World,
                     world_size: pygame.Vector2 | None = None) -> list[tuple[int, int]]:
    """Detecta colisiones AABB entre hitboxes y devuelve los pares que se tocan.

    Con world_size, dos entidades a lados opuestos del borde del mundo también chocan.
    No decide qué pasa en cada choque: eso le corresponde a las reglas de colisión.
    """
    boxes = [(ent, c_hb, hitbox_center(c_t, c_hb))
             for ent, (c_t, c_hb) in world.get_components(CTransform, CHitBox)]
    collisions = []
    for i, (ent_a, hb_a, center_a) in enumerate(boxes):
        for ent_b, hb_b, center_b in boxes[i + 1:]:
            if not _can_collide(hb_a, hb_b):
                continue
            d = center_delta(center_a, center_b, world_size)
            if (abs(d.x) < (hb_a.size.x + hb_b.size.x) / 2
                    and abs(d.y) < (hb_a.size.y + hb_b.size.y) / 2):
                collisions.append((ent_a, ent_b))
    return collisions
