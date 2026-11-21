"""Persiana entre pantallas, como la del Bosconian original: dos bandas verde menta se cierran
desde arriba y desde abajo sobre el campo de juego, se cambia de escena con el campo cubierto y
se abren de nuevo. La barra lateral queda fuera: se dibuja después."""

import esper
import pygame

from src.ecs.components.c_shutter import CShutter, ShutterState


def shutter_start(world: esper.World, target: str) -> bool:
    """Empieza a cerrar la persiana para ir a `target`, si esa escena se alcanza con persiana
    y no hay otra en marcha. Devuelve True si empezó."""
    for _, c_sh in world.get_component(CShutter):
        if target in c_sh.scenes and c_sh.state == ShutterState.IDLE:
            c_sh.state, c_sh.target, c_sh.time = ShutterState.CLOSING, target, 0.0
            return True
    return False


def system_shutter(world: esper.World, delta_time: float) -> str | None:
    """Avanza la persiana. En el frame en que el campo queda cubierto devuelve la escena de
    destino (es el momento de cambiarla) y empieza a abrirse."""
    for _, c_sh in world.get_component(CShutter):
        if c_sh.state == ShutterState.CLOSING:
            c_sh.time += delta_time
            if c_sh.time >= c_sh.close_seconds:
                c_sh.state, c_sh.time = ShutterState.OPENING, 0.0
                return c_sh.target
        elif c_sh.state == ShutterState.OPENING:
            c_sh.time += delta_time
            if c_sh.time >= c_sh.open_seconds:
                c_sh.state, c_sh.target = ShutterState.IDLE, None
    return None


def shutter_cover(c_sh: CShutter) -> float:
    """Cuánto del campo cubren las bandas: 0 abierta, 1 cerrada del todo."""
    if c_sh.state == ShutterState.CLOSING:
        return min(c_sh.time / c_sh.close_seconds, 1.0)
    if c_sh.state == ShutterState.OPENING:
        return 1.0 - min(c_sh.time / c_sh.open_seconds, 1.0)
    return 0.0


def system_shutter_rendering(world: esper.World, screen: pygame.Surface) -> None:
    for _, c_sh in world.get_component(CShutter):
        cover = shutter_cover(c_sh)
        if cover <= 0:
            continue
        stage = c_sh.stage
        band = round(stage.h / 2 * cover)  # alto de cada banda
        screen.fill(c_sh.color, pygame.Rect(stage.left, stage.top, stage.w, band))
        screen.fill(c_sh.color, pygame.Rect(stage.left, stage.bottom - band, stage.w, band))
