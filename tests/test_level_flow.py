"""Pruebas del flujo de niveles (#69), la dificultad (#70) y el HUD (#68)."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import pygame

from src.engine.data_loader import ConfigError, level_numbers, load_level
from src.engine.difficulty import difficulty_params
from src.engine.game_engine import GameEngine
from src.engine.game_state import GameState
from src.engine.level_flow import after_level_cleared, after_player_died
from tests.test_game_state import CFG


class FlowTests(unittest.TestCase):
    def test_siguiente_nivel_y_victoria_tras_el_ultimo(self):
        s = GameState(dict(CFG))
        self.assertEqual(after_level_cleared(s, [1, 2, 3]), "PLAY")
        self.assertEqual(s.level, 2)
        s.level = 3
        self.assertEqual(after_level_cleared(s, [1, 2, 3]), "VICTORY")
        self.assertEqual(s.level, 3)

    def test_muerte_repite_nivel_y_sin_vidas_va_a_derrota(self):
        s = GameState(dict(CFG))
        self.assertEqual(after_player_died(s), "PLAY")
        self.assertEqual(s.lives, 3)
        s.lives = 1
        self.assertEqual(after_player_died(s), "PLAY")  # llega a 0: aún queda una vida
        self.assertEqual(s.lives, 0)
        self.assertEqual(after_player_died(s), "DEFEAT")  # muere con el contador en 0


class DifficultyTests(unittest.TestCase):
    def test_sin_campo_usa_el_valor_por_defecto(self):
        self.assertEqual(difficulty_params({})["difficulty"], 1)

    def test_se_acota_al_rango_definido(self):
        self.assertEqual(difficulty_params({"difficulty": 99})["difficulty"], 5)

    def test_mas_dificultad_alertas_mas_tempranas(self):
        a, b = difficulty_params({"difficulty": 1}), difficulty_params({"difficulty": 5})
        self.assertLess(b["yellow_after"], a["yellow_after"])
        self.assertLess(b["red_after"], a["red_after"])

    def test_nivel_con_difficulty_invalida_falla(self):
        import json, tempfile
        from src.engine import data_loader
        lvl = {"round": 1, "difficulty": 0, "player_start": {"x": 0, "y": 0}, "bases": []}
        with tempfile.TemporaryDirectory() as d:
            old = data_loader.LEVELS_DIR
            data_loader.LEVELS_DIR = d
            try:
                with open(os.path.join(d, "level_01.json"), "w") as f:
                    json.dump(lvl, f)
                with self.assertRaises(ConfigError):
                    load_level(1)
            finally:
                data_loader.LEVELS_DIR = old


class SceneIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        self.engine._apply_scene_change("PLAY")
        self.scene = self.engine._current_scene

    def test_el_nivel_del_engine_es_el_del_estado(self):
        self.engine.level = 4
        self.assertEqual(self.engine.state.level, 4)

    def test_nivel_superado_pide_la_siguiente_escena(self):
        self.scene.level_cleared()
        self.assertEqual(self.engine._next_scene, "PLAY")
        self.assertEqual(self.engine.state.level, 2)

    def test_superar_el_ultimo_nivel_es_victoria(self):
        self.engine.state.level = level_numbers()[-1]
        self.scene.level_cleared()
        self.assertEqual(self.engine._next_scene, "VICTORY")

    def test_muerte_descuenta_vida_y_repite(self):
        self.scene.player_died()
        self.assertEqual(self.engine.state.lives, 3)
        self.assertEqual(self.engine._next_scene, "PLAY")

    def test_hud_se_dibuja_y_cambia_con_el_puntaje(self):
        """La barra lateral la dibuja el motor tras la escena: se mira la pantalla completa."""
        self.engine._draw()
        before = pygame.image.tobytes(self.engine.screen, "RGB")
        self.engine.state.add_score(1230)
        self.engine._draw()
        self.assertNotEqual(before, pygame.image.tobytes(self.engine.screen, "RGB"))

    def test_hud_con_mas_de_cuatro_vidas_muestra_el_total(self):
        self.engine._draw()
        base = pygame.image.tobytes(self.engine.screen, "RGB")
        self.engine.state.lives = 6
        self.engine._draw()
        self.assertNotEqual(base, pygame.image.tobytes(self.engine.screen, "RGB"))

    def test_jugar_desde_el_titulo_reinicia_la_partida_y_conserva_record(self):
        s = self.engine.state
        s.add_score(60000)
        s.level = 1
        self.engine.start_game()
        self.assertEqual((s.score, s.lives, s.hi_score), (0, 4, 60000))

    def test_escenas_finales_se_crean_y_dibujan(self):
        for name in ("VICTORY", "DEFEAT"):
            self.engine._apply_scene_change(name)
            self.engine._current_scene.do_update(0.1)
            self.engine._current_scene.do_draw(pygame.Surface((256, 208)))


if __name__ == "__main__":
    unittest.main()
