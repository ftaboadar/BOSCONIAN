"""Condición de alerta del nivel: VERDE -> AMARILLA -> ROJA (por tiempo), con un sonido
en cada cambio. Destruir una base devuelve un rato a VERDE; de ROJA ya no se baja."""

import esper

from src.ecs.components.c_alert import AlertLevel, CAlert
from src.ecs.components.c_enemy_state import CEnemyState
from src.ecs.components.c_velocity import CVelocity
from src.engine.sfx import play_sound

SOUNDS = {AlertLevel.GREEN: "alert_green", AlertLevel.YELLOW: "alert_yellow",
          AlertLevel.RED: "alert_red"}


def system_alert(world: esper.World, delta_time: float) -> None:
    for _, c_alert in world.get_component(CAlert):
        if c_alert.level == AlertLevel.RED:
            continue
        c_alert.elapsed += delta_time
        if c_alert.elapsed >= c_alert.red_after:
            _change(c_alert, AlertLevel.RED)
            # Los que ya estaban persiguiendo también aceleran, no solo los nuevos.
            for _, (c_v, _c_s) in world.get_components(CVelocity, CEnemyState):
                c_v.vel *= c_alert.red_speed_factor
        elif c_alert.level == AlertLevel.GREEN:
            c_alert.green_left -= delta_time
            if c_alert.green_left <= 0:
                _change(c_alert, AlertLevel.YELLOW)


def enemy_pace(world: esper.World) -> tuple[float, float]:
    """Cómo salen los enemigos con la alerta actual: (ritmo, velocidad), como factores
    sobre lo normal del nivel. Ritmo 0 es que no salen. Sin alerta en el mundo, lo normal."""
    for _, c_alert in world.get_component(CAlert):
        if c_alert.level == AlertLevel.GREEN:
            return 0.0, 1.0
        if c_alert.level == AlertLevel.RED:
            return c_alert.red_spawn_factor, c_alert.red_speed_factor
    return 1.0, 1.0


def alert_base_destroyed(world: esper.World) -> None:
    """Cayó una base: la alerta vuelve a VERDE durante `calm_seconds` (salvo en ROJA)."""
    for _, c_alert in world.get_component(CAlert):
        if c_alert.level == AlertLevel.RED:
            continue
        # max: una base destruida al empezar no acorta el VERDE inicial.
        c_alert.green_left = max(c_alert.green_left, c_alert.calm_seconds)
        if c_alert.level != AlertLevel.GREEN:
            _change(c_alert, AlertLevel.GREEN)


def _change(c_alert: CAlert, level: AlertLevel) -> None:
    c_alert.level = level
    play_sound(SOUNDS[level])
