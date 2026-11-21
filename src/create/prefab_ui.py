"""Entidades de la interfaz fija del juego, que no pertenecen a ninguna escena: la barra
lateral y la persiana entre pantallas."""

import esper
import pygame

from src.ecs.components.c_hud import CHud
from src.ecs.components.c_shutter import CShutter
from src.engine.data_loader import ConfigError, require_keys
from src.engine.service_locator import color_from_cfg

HUD_KEYS = ("texts", "colors", "rows", "condition_bar", "life_icons", "letter_gap",
            "trimmed_letters")
SHUTTER_KEYS = ("close_seconds", "open_seconds", "color", "to")


def create_hud(world: esper.World, cfg: dict, font: pygame.font.Font, icon: pygame.Surface,
               icons_max: int, panel: pygame.Rect) -> int:
    """Barra lateral según hud.json. `icon` es la mini-nave de cada vida."""
    require_keys(cfg, HUD_KEYS, "hud.json")
    colors = {k: color_from_cfg(cfg["colors"][k]) for k in ("text", "highlight", "bar_text")}
    condition = {name: color_from_cfg(c) for name, c in cfg["colors"]["condition"].items()}
    bar = pygame.Rect(panel.left, cfg["condition_bar"]["y"], panel.w, cfg["condition_bar"]["h"])
    return world.create_entity(CHud(
        font, icon, icons_max, pygame.Rect(panel), cfg["texts"], colors, condition, cfg["rows"],
        bar, cfg["life_icons"]["y"], cfg["life_icons"]["spacing"], cfg["letter_gap"],
        cfg["trimmed_letters"]))


def create_shutter(world: esper.World, cfg: dict, stage: pygame.Rect) -> int:
    """Persiana según la sección `shutter` de world.json, sobre el campo de juego `stage`."""
    require_keys(cfg, SHUTTER_KEYS, "world.json shutter")
    if cfg["close_seconds"] <= 0 or cfg["open_seconds"] <= 0:
        raise ConfigError("world.json shutter: close_seconds y open_seconds deben ser mayores que 0")
    return world.create_entity(CShutter(
        cfg["close_seconds"], cfg["open_seconds"], color_from_cfg(cfg["color"]),
        tuple(cfg["to"]), pygame.Rect(stage)))
