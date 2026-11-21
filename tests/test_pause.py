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
        # Sin BLAST OFF!: si no, la cuenta inicial ya impide moverse y las pruebas de pausa
        # pasarían aunque la pausa no congelara nada.
        self.scene.clock.blast_left = 0

    def tearDown(self) -> None:
        self.engine._clean()

    def test_player_moves_when_not_paused(self) -> None:
        """Control: sin pausa el jugador sí se mueve, así la prueba de abajo tiene sentido."""
        before = self.scene.world.component_for_entity(self.scene.player, CTransform).pos.copy()
        self.scene.do_update(0.5)
        after = self.scene.world.component_for_entity(self.scene.player, CTransform).pos
        self.assertNotEqual(before, after)

    def test_pause_freezes_blast_off_countdown(self) -> None:
        self.scene.clock.blast_left = 2.0
        self.scene.do_action("PAUSE", Phase.START)
        for _ in range(30):
            self.scene.do_update(0.1)
        self.assertEqual(self.scene.clock.blast_left, 2.0)

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

    def act(self, *actions: str) -> None:
        for action in actions:
            self.scene.do_action(action, Phase.START)
            self.scene.do_action(action, Phase.END)

    def test_pause_menu_has_the_title_options_plus_exit(self) -> None:
        self.act("PAUSE")
        actions = [item["action"] for item in self.scene.pause_menu.items]
        title = [item["action"] for item in self.engine.cfg_menu["title_items"]]
        self.assertEqual(actions, title + ["EXIT"])

    def test_play_in_pause_menu_resumes(self) -> None:
        self.act("PAUSE", "SELECT")  # JUGAR es la primera opción
        self.assertFalse(self.scene.paused)
        self.assertIsNone(self.engine._next_scene)

    def test_exit_in_pause_menu_goes_to_title(self) -> None:
        self.act("PAUSE", "UP", "SELECT")  # arriba desde JUGAR: la última opción, salir
        self.assertIsNone(self.engine._next_scene)  # primero pide confirmación
        self.assertTrue(self.scene.confirm_exit)
        self.act("SELECT")
        self.assertEqual(self.engine._next_scene, "TITLE")

    def test_instructions_open_inside_pause_and_close_back_to_menu(self) -> None:
        self.act("PAUSE", "DOWN", "DOWN", "SELECT")
        self.assertIsNotNone(self.scene.pause_page)
        self.scene.do_draw(self.engine.screen)
        self.act("BACK")  # ESC cierra la página, no pide salir
        self.assertIsNone(self.scene.pause_page)
        self.assertFalse(self.scene.confirm_exit)
        self.assertTrue(self.scene.paused)
        self.assertIsNone(self.engine._next_scene)

    def test_choosing_another_level_in_pause_starts_it(self) -> None:
        self.engine.state.add_score(500)
        self.act("PAUSE", "DOWN", "RIGHT")
        self.assertEqual(self.engine.level, 1)  # aún no se aplica
        self.act("UP", "SELECT")
        self.assertEqual(self.engine.level, 2)
        self.assertEqual(self.engine.state.score, 0)  # partida nueva
        self.assertEqual(self.engine._next_scene, "CUTSCENE")

    def test_level_choice_is_forgotten_when_resuming_with_p(self) -> None:
        self.act("PAUSE", "DOWN", "RIGHT", "PAUSE")
        self.assertEqual(self.engine.level, 1)
        self.act("PAUSE", "SELECT")  # JUGAR reanuda el mismo nivel
        self.assertFalse(self.scene.paused)
        self.assertIsNone(self.engine._next_scene)

    def test_draw_while_paused_does_not_fail(self) -> None:
        self.scene.do_action("PAUSE", Phase.START)
        self.scene.do_draw(self.engine.screen)


if __name__ == "__main__":
    unittest.main()
