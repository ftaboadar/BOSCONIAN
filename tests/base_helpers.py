"""Ayuda para las pruebas de bases: un disparo y el final de ese frame."""

import os
import sys

sys.path.insert(0, os.getcwd())

from src.ecs.systems.s_base_damage import damage_base_part
from src.ecs.systems.s_destroy import system_destroy
from src.ecs.systems.s_explode import system_explode
from src.engine.data_loader import load_json

EXPLOSIONS = load_json("assets/cfg/explosions.json")


def hit_base_part(world, part, shot_dir) -> int:
    """Aplica un disparo a una torreta o al núcleo y cierra el frame como lo hace el nivel:
    lo marcado con CDestroy explota (y suena) y se borra. Devuelve los puntos ganados."""
    points = damage_base_part(world, part, shot_dir)
    system_explode(world, EXPLOSIONS)
    system_destroy(world)
    return points
