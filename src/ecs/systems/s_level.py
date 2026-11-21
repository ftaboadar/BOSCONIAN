"""Cuentas del nivel: BLAST OFF! al empezar y la espera para ver la explosión de la nave."""

import esper

from src.ecs.components.c_level_clock import CLevelClock
from src.ecs.components.c_player_ship import CPlayerShip


def system_blast_off(world: esper.World, delta_time: float) -> bool:
    """Avanza la cuenta de BLAST OFF!. Devuelve True mientras dure: el nivel aún no empieza."""
    counting = False
    for _, c_clock in world.get_component(CLevelClock):
        if c_clock.blast_left > 0:
            c_clock.blast_left = max(0.0, c_clock.blast_left - delta_time)
            counting = True
    return counting


def system_player_death(world: esper.World, delta_time: float) -> bool:
    """Cuando ya no hay nave, espera `death_wait` segundos para que se vea su explosión.
    Devuelve True en el frame en que la espera termina."""
    for _, c_clock in world.get_component(CLevelClock):
        if c_clock.death_left is None:
            if world.get_component(CPlayerShip):
                continue
            c_clock.death_left = c_clock.death_wait
        c_clock.death_left -= delta_time
        if c_clock.death_left <= 0:
            return True
    return False
