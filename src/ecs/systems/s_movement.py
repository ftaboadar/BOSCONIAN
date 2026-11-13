import esper

from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity


def system_movement(world: esper.World, delta_time: float) -> None:
    for _, (c_t, c_v) in world.get_components(CTransform, CVelocity):
        c_t.pos += c_v.vel * delta_time
