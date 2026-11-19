"""ESC sale al título desde el nivel, también en pausa y durante BLAST OFF! (#30)."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

from src.engine.game_engine import GameEngine
from src.engine.input.command import Phase


class ExitToTitleTests(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        self.engine._apply_scene_change("PLAY")
        self.scene = self.engine._current_scene

    def test_esc_durante_blast_off_sale_al_titulo(self):
        self.scene.do_action("BACK", Phase.START)
        self.assertEqual(self.engine._next_scene, "TITLE")

    def test_esc_jugando_sale_al_titulo(self):
        self.scene.do_update(self.engine.cfg_world["blast_off"]["seconds"] + 0.1)
        self.scene.do_action("BACK", Phase.START)
        self.assertEqual(self.engine._next_scene, "TITLE")

    def test_esc_en_pausa_sale_al_titulo(self):
        self.scene.do_action("PAUSE", Phase.START)
        self.scene.do_action("BACK", Phase.START)
        self.assertEqual(self.engine._next_scene, "TITLE")

    def test_soltar_esc_no_hace_nada(self):
        self.scene.do_action("BACK", Phase.END)
        self.assertIsNone(self.engine._next_scene)


if __name__ == "__main__":
    unittest.main()
