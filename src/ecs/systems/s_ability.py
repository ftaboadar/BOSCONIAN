"""Segunda habilidad especial: escudo de energía (tecla X), no letal.

El jugador recoge un ítem que aparece en el mundo (visible en el minimapa); cada ítem da un uso,
hasta `max_charges`. X gasta un uso y activa el escudo `duration` segundos: en ese tiempo las
colisiones de la nave no destruyen nada (ni a ella ni a lo que toca). Todo sale de ability.json."""

import random

import esper
import pygame

from src.create.prefab_creator import create_ability_item, create_shield_aura
from src.ecs.components.c_ability import (
    CAbility,
    CAbilityItem,
    CItemSpawner,
    CShield,
    CShieldAura,
)
from src.ecs.components.c_destroy import CDestroy
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.engine.input.command import Phase
from src.engine.service_locator import ServiceLocator, color_from_cfg

_rng = random.Random()


def system_ability_input(world: esper.World, action: str, phase: Phase, enabled: bool) -> None:
    """X deja una pulsación pendiente; en pausa o BLAST OFF! (`enabled` False) se ignora."""
    if action != "SPECIAL" or phase != Phase.START or not enabled:
        return
    for _, c_a in world.get_component(CAbility):
        c_a.trigger = True


def system_ability(world: esper.World, delta_time: float, shield_cfg: dict) -> bool:
    """Descuenta el escudo activo y atiende la pulsación de X. Devuelve True si se activó en este frame.

    Con el escudo ya activo o sin usos, la pulsación se pierde (no se gasta nada)."""
    activated = False
    for ent, c_a in world.get_component(CAbility):
        shield = world.try_component(ent, CShield)
        if shield is not None:
            shield.remaining -= delta_time
            if shield.remaining <= 0:
                world.remove_component(ent, CShield)
                shield = None
        if c_a.trigger:
            c_a.trigger = False
            if shield is None and c_a.charges > 0:
                c_a.charges -= 1
                world.add_component(ent, CShield(c_a.duration))
                create_shield_aura(world, ent, shield_cfg)
                activated = True
    return activated


def system_shield_aura(world: esper.World) -> None:
    """El anillo sigue a la nave, parpadea en el último tramo y desaparece al acabar el escudo."""
    for ent, (c_au, c_t, c_s) in world.get_components(CShieldAura, CTransform, CSurface):
        owner = c_au.owner
        shield = world.try_component(owner, CShield) if world.entity_exists(owner) else None
        if shield is None:
            if not world.has_component(ent, CDestroy):
                world.add_component(ent, CDestroy(explodes=False))
            continue
        c_t.pos = pygame.Vector2(world.component_for_entity(owner, CTransform).pos)
        blinking = shield.remaining < c_au.blink_seconds and int(shield.remaining * c_au.blink_rate) % 2 == 1
        c_s.surf = c_au.blank if blinking else c_au.surf


def collect_item(world: esper.World, player: int, item: int) -> bool:
    """El jugador toca un ítem: gana un uso y el ítem desaparece. Con el límite alcanzado lo deja en su sitio."""
    c_a = world.try_component(player, CAbility)
    if c_a is None or c_a.charges >= c_a.max_charges:
        return False
    c_a.charges += 1
    world.add_component(item, CDestroy(explodes=False))
    return True


def system_ability_item_spawner(world: esper.World, player_pos: pygame.Vector2,
                                world_size: pygame.Vector2, item_cfg: dict, delta_time: float,
                                rng: random.Random = _rng) -> None:
    """Cada intervalo, con la probabilidad del nivel, aparece un ítem cerca del jugador (a una distancia
    entre `min_distance` y `max_distance`). Solo hay uno a la vez y no sale si el jugador ya tiene el máximo."""
    for _, c_sp in world.get_component(CItemSpawner):
        c_sp.timer += delta_time
        if c_sp.timer < c_sp.interval:
            continue
        c_sp.timer -= c_sp.interval
        if world.get_component(CAbilityItem):
            continue
        if any(c_a.charges >= c_a.max_charges for _, c_a in world.get_component(CAbility)):
            continue
        if rng.random() >= c_sp.chance:
            continue
        offset = pygame.Vector2(rng.uniform(item_cfg["min_distance"], item_cfg["max_distance"]), 0)
        pos = player_pos + offset.rotate(rng.uniform(0, 360))
        create_ability_item(world, pygame.Vector2(pos.x % world_size.x, pos.y % world_size.y), item_cfg)


def system_ability_hud(world: esper.World, screen: pygame.Surface, shield_cfg: dict,
                       hud_cfg: dict, viewport: pygame.Rect) -> None:
    """Abajo a la izquierda del campo de juego: `X ESCUDO usos/máx`, y una barra con el tiempo que le queda
    al escudo activo. No se muestra mientras el jugador no tenga usos ni escudo."""
    font = ServiceLocator.fonts.get("main")
    for ent, c_a in world.get_component(CAbility):
        shield = world.try_component(ent, CShield)
        if c_a.charges == 0 and shield is None:
            continue
        color = color_from_cfg(hud_cfg["active_color" if shield else "text_color"])
        text = font.render(f"X {shield_cfg['name']} {c_a.charges}/{c_a.max_charges}", False, color)
        rect = text.get_rect(left=viewport.left + hud_cfg["x"], bottom=viewport.bottom - hud_cfg["bottom"])
        screen.blit(text, rect)
        if shield:
            width = round(rect.width * max(0.0, shield.remaining) / c_a.duration)
            pygame.draw.rect(screen, color, (rect.left, rect.top - hud_cfg["bar_h"] - 1, width, hud_cfg["bar_h"]))
