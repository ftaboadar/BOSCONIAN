"""Valores de assets/cfg/hud.json con los nombres que usan las pruebas de la barra lateral."""

import os
import sys

sys.path.insert(0, os.getcwd())

from src.engine.data_loader import load_json
from src.engine.service_locator import color_from_cfg

HUD = load_json("assets/cfg/hud.json")
ROWS = HUD["rows"]
BAR_Y, BAR_H = HUD["condition_bar"]["y"], HUD["condition_bar"]["h"]
ICONS_Y, ICON_SPACING = HUD["life_icons"]["y"], HUD["life_icons"]["spacing"]
WHITE = color_from_cfg(HUD["colors"]["text"])
RED = color_from_cfg(HUD["colors"]["highlight"])
CONDITION_COLORS = {name: color_from_cfg(c) for name, c in HUD["colors"]["condition"].items()}
