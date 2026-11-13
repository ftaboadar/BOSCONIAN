import esper
import pygame

from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_world import CWorld


def system_wraparound(world: esper.World, world_size: pygame.Vector2) -> None:
    """Si una entidad sale por un lado del mundo aparece por el opuesto."""
    for _, (c_t, _c_w) in world.get_components(CTransform, CWorld):
        c_t.pos.x %= world_size.x
        c_t.pos.y %= world_size.y
