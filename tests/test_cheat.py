"""Pruebas del modo trampa (#34): F1 alterna la invulnerabilidad del jugador."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.engine.game_engine import GameEngine
from src.engine.input.command import Phase


class TestCheat(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = GameEngine()
        self.engine._apply_scene_change("PLAY")
        self.scene = self.engine._current_scene

    def tearDown(self) -> None:
        self.engine._clean()

    def test_cheat_off_by_default_and_death_costs_life(self) -> None:
        lives = self.engine.state.lives
        self.assertFalse(self.engine.state.cheat)
        self.scene.player_died()
        self.assertEqual(self.engine.state.lives, lives - 1)

    def test_cheat_action_toggles(self) -> None:
        self.scene.do_action("CHEAT", Phase.START)
        self.assertTrue(self.engine.state.cheat)
        self.scene.do_action("CHEAT", Phase.START)
        self.assertFalse(self.engine.state.cheat)

    def test_cheat_makes_player_invulnerable(self) -> None:
        lives = self.engine.state.lives
        self.scene.do_action("CHEAT", Phase.START)
        self.engine._next_scene = None
        self.scene.player_died()
        self.assertEqual(self.engine.state.lives, lives)
        self.assertIsNone(self.engine._next_scene)

    def test_cheat_toggles_while_paused(self) -> None:
        self.scene.do_action("PAUSE", Phase.START)
        self.scene.do_action("CHEAT", Phase.START)
        self.assertTrue(self.engine.state.cheat)

    def test_new_game_turns_cheat_off(self) -> None:
        self.engine.state.cheat = True
        self.engine.state.reset()
        self.assertFalse(self.engine.state.cheat)

    def test_draw_with_cheat_does_not_fail(self) -> None:
        self.scene.do_action("CHEAT", Phase.START)
        self.scene.do_draw(self.engine.screen)


if __name__ == "__main__":
    unittest.main()
