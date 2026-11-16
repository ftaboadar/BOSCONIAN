"""Pruebas de la pausa del nivel (#30): congela el mundo y alterna con P."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.ecs.components.c_transform import CTransform
from src.engine.game_engine import GameEngine
from src.engine.input.command import Phase


class TestPause(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = GameEngine()
        self.engine._apply_scene_change("PLAY")
        self.scene = self.engine._current_scene

    def tearDown(self) -> None:
        self.engine._clean()

    def test_pause_toggles_with_pause_action(self) -> None:
        self.scene.do_action("PAUSE", Phase.START)
        self.assertTrue(self.scene.paused)
        self.scene.do_action("PAUSE", Phase.START)
        self.assertFalse(self.scene.paused)

    def test_player_does_not_move_while_paused(self) -> None:
        self.scene.do_action("PAUSE", Phase.START)
        before = self.scene.world.component_for_entity(self.scene.player, CTransform).pos.copy()
        for _ in range(10):
            self.scene.do_update(0.1)
        after = self.scene.world.component_for_entity(self.scene.player, CTransform).pos
        self.assertEqual(before, after)

    def test_select_in_pause_goes_to_title(self) -> None:
        self.scene.do_action("PAUSE", Phase.START)
        self.scene.do_action("SELECT", Phase.START)
        self.assertEqual(self.engine._next_scene, "TITLE")

    def test_draw_while_paused_does_not_fail(self) -> None:
        self.scene.do_action("PAUSE", Phase.START)
        self.scene.do_draw(self.engine.screen)


if __name__ == "__main__":
    unittest.main()
