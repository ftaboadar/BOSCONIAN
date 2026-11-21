import esper

from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_destroy import CDestroy
from src.ecs.components.c_surface import CSurface


def system_animation(world: esper.World, delta_time: float) -> None:
    """Avanza las animaciones cuadro a cuadro; una animación sin loop que termina
    marca su entidad con CDestroy."""
    for ent, (c_s, c_a) in world.get_components(CSurface, CAnimation):
        c_a.curr_time += delta_time
        if c_a.curr_time < c_a.frame_time:
            continue
        c_a.curr_time -= c_a.frame_time
        c_a.curr_frame += 1

        if c_a.curr_frame >= len(c_a.frames):
            if c_a.loop:
                c_a.curr_frame = 0
            else:
                world.add_component(ent, CDestroy())
                continue

        c_s.surf = c_a.sheet.subsurface(c_a.frames[c_a.curr_frame])
