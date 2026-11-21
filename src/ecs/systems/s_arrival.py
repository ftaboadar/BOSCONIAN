import esper

from src.ecs.components.c_arrival import CArrival
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity


def system_arrival(world: esper.World, delta_time: float) -> None:
    """Al cumplirse el tiempo de viaje, coloca la entidad en su destino y la detiene.

    Debe correr después de system_movement, que es quien la mueve mientras viaja."""
    for ent, (c_a, c_t, c_v) in world.get_components(CArrival, CTransform, CVelocity):
        c_a.remaining -= delta_time
        if c_a.remaining <= 0:
            c_t.pos.update(c_a.target)
            c_v.vel.update(0, 0)
            world.remove_component(ent, CArrival)
