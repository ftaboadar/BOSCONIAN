"""Pruebas de los 10 niveles definidos en JSON (#29)."""

import json
import os
import sys
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import pygame

from src.engine import data_loader
from src.engine.camera import wrap_delta
from src.engine.data_loader import ConfigError, level_numbers, load_json, load_level

WORLD_CFG = load_json("assets/cfg/world.json")
WORLD = pygame.Vector2(WORLD_CFG["world_size"]["w"], WORLD_CFG["world_size"]["h"])
DIFFICULTY = load_json("assets/cfg/difficulty.json")
RESOURCES = load_json("assets/cfg/resources.json")
OBSTACLES = load_json("assets/cfg/obstacles.json")
LEVELS = {n: load_level(n) for n in level_numbers()}


def distance(a: dict, b: dict) -> float:
    return wrap_delta(pygame.Vector2(a["x"] - b["x"], a["y"] - b["y"]), WORLD).length()


class LevelsTests(unittest.TestCase):
    def test_hay_10_niveles_consecutivos(self):
        self.assertEqual(level_numbers(), list(range(1, 11)))

    def test_la_ronda_coincide_con_el_numero(self):
        for n, level in LEVELS.items():
            self.assertEqual(level["round"], n)

    def test_dificultad_existe_y_no_baja(self):
        previous = 0
        for n, level in LEVELS.items():
            self.assertIn(str(level["difficulty"]), DIFFICULTY["levels"], f"nivel {n}")
            self.assertGreaterEqual(level["difficulty"], previous, f"nivel {n}")
            previous = level["difficulty"]

    def test_bases_dentro_del_mundo_y_lejos_del_jugador(self):
        for n, level in LEVELS.items():
            self.assertGreater(len(level["bases"]), 0, f"nivel {n}")
            for b in level["bases"]:
                self.assertTrue(0 <= b["x"] < WORLD.x and 0 <= b["y"] < WORLD.y, f"nivel {n}")
                self.assertGreaterEqual(distance(b, level["player_start"]),
                                        OBSTACLES["spawn"]["min_distance_player"], f"nivel {n}")

    def test_bases_no_se_superponen(self):
        for n, level in LEVELS.items():
            bases = level["bases"]
            for i, a in enumerate(bases):
                for b in bases[i + 1:]:
                    self.assertGreater(distance(a, b), 100, f"nivel {n}")

    def test_cada_nivel_tiene_obstaculos(self):
        for n, level in LEVELS.items():
            self.assertGreater(sum(level["obstacles"].values()), 0, f"nivel {n}")

    def test_habilidad_especial_definida_por_nivel(self):
        for n, level in LEVELS.items():
            self.assertIsInstance(level["special_shot"], bool, f"nivel {n}")
        self.assertTrue(any(level["special_shot"] for level in LEVELS.values()))

    def test_la_musica_de_cada_nivel_esta_registrada(self):
        for n, level in LEVELS.items():
            self.assertIn(level["music"], RESOURCES["music"], f"nivel {n}")
            self.assertTrue(os.path.isfile(RESOURCES["music"][level["music"]]), level["music"])


class ValidationTests(unittest.TestCase):
    def _load_with(self, **extra):
        level = {"round": 1, "player_start": {"x": 0, "y": 0}, "bases": [], **extra}
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "level_01.json"), "w", encoding="utf-8") as f:
                json.dump(level, f)
            old = data_loader.LEVELS_DIR
            data_loader.LEVELS_DIR = tmp
            try:
                return load_level(1)
            finally:
                data_loader.LEVELS_DIR = old

    def test_special_shot_debe_ser_booleano(self):
        with self.assertRaises(ConfigError):
            self._load_with(special_shot="si")

    def test_music_debe_ser_texto(self):
        with self.assertRaises(ConfigError):
            self._load_with(music=3)

    def test_valores_validos_cargan(self):
        level = self._load_with(special_shot=True, music="xenostar")
        self.assertTrue(level["special_shot"])


if __name__ == "__main__":
    unittest.main()
