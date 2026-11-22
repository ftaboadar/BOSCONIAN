"""Pruebas del soporte de gamepad (#38): stick izquierdo, A/X y B/círculo -> acciones lógicas."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.engine.data_loader import load_json
from src.engine.game_engine import GameEngine
from src.engine.input.command import CommandMap, Phase


def _map() -> CommandMap:
    cfg = load_json("assets/cfg/input.json")
    return CommandMap(cfg["keyboard"], cfg["gamepad"])


def _axis(axis: int, value: float, pad: int = 0) -> pygame.event.Event:
    return pygame.event.Event(pygame.JOYAXISMOTION, instance_id=pad, axis=axis, value=value)


def _button(kind: int, button: int) -> pygame.event.Event:
    return pygame.event.Event(kind, instance_id=0, button=button)


class TestCommandMapGamepad(unittest.TestCase):
    def setUp(self) -> None:
        self.map = _map()

    def test_stick_left_starts_and_ends_direction(self) -> None:
        self.assertEqual(self.map.translate(_axis(0, -1.0)), [("LEFT", Phase.START)])
        self.assertEqual(self.map.translate(_axis(0, 0.0)), [("LEFT", Phase.END)])

    def test_stick_vertical_axis(self) -> None:
        self.assertEqual(self.map.translate(_axis(1, -0.9)), [("UP", Phase.START)])
        self.assertEqual(self.map.translate(_axis(1, 0.9)), [("UP", Phase.END), ("DOWN", Phase.START)])

    def test_deadzone_ignores_small_tilt(self) -> None:
        self.assertEqual(self.map.translate(_axis(0, 0.2)), [])

    def test_continuous_tilt_does_not_repeat_start(self) -> None:
        self.map.translate(_axis(0, 0.7))
        self.assertEqual(self.map.translate(_axis(0, 1.0)), [])

    def test_diagonal_gives_two_directions(self) -> None:
        self.map.translate(_axis(0, 1.0))
        self.assertEqual(self.map.translate(_axis(1, -1.0)), [("UP", Phase.START)])

    def test_other_axes_ignored(self) -> None:
        self.assertEqual(self.map.translate(_axis(2, 1.0)), [])

    def test_a_is_fire_and_select(self) -> None:
        down = self.map.translate(_button(pygame.JOYBUTTONDOWN, 0))
        self.assertEqual(down, [("FIRE", Phase.START), ("SELECT", Phase.START)])
        up = self.map.translate(_button(pygame.JOYBUTTONUP, 0))
        self.assertEqual(up, [("FIRE", Phase.END), ("SELECT", Phase.END)])

    def test_b_is_special(self) -> None:
        self.assertIn(("SPECIAL", Phase.START), self.map.translate(_button(pygame.JOYBUTTONDOWN, 1)))

    def test_unmapped_button_ignored(self) -> None:
        self.assertEqual(self.map.translate(_button(pygame.JOYBUTTONDOWN, 15)), [])

    def test_hat_gives_directions(self) -> None:
        hat = pygame.event.Event(pygame.JOYHATMOTION, instance_id=0, hat=0, value=(0, 1))
        self.assertEqual(self.map.translate(hat), [("UP", Phase.START)])

    def test_disconnect_releases_held_direction(self) -> None:
        self.map.translate(_axis(0, 1.0))
        gone = pygame.event.Event(pygame.JOYDEVICEREMOVED, instance_id=0)
        self.assertEqual(self.map.translate(gone), [("RIGHT", Phase.END)])

    def test_keyboard_still_works(self) -> None:
        key = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z)
        self.assertEqual(self.map.translate(key), [("FIRE", Phase.START)])

    def test_keyboard_and_gamepad_alternate(self) -> None:
        self.map.translate(_axis(0, -1.0))
        key = pygame.event.Event(pygame.KEYUP, key=pygame.K_LEFT)
        self.assertEqual(self.map.translate(key), [("LEFT", Phase.END)])
        self.assertEqual(self.map.translate(_axis(0, 0.0)), [("LEFT", Phase.END)])

    def test_works_without_gamepad_cfg(self) -> None:
        plain = CommandMap(load_json("assets/cfg/input.json")["keyboard"])
        self.assertEqual(plain.translate(_axis(0, 1.0)), [("RIGHT", Phase.START)])


class TestEngineGamepad(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = GameEngine()

    def tearDown(self) -> None:
        self.engine._clean()

    def test_stick_moves_player_in_play(self) -> None:
        from src.ecs.components.c_transform import CTransform
        self.engine._apply_scene_change("PLAY")
        scene = self.engine._current_scene
        scene.clock.blast_left = 0
        before = scene.world.component_for_entity(scene.player, CTransform).pos.copy()
        pygame.event.clear()
        pygame.event.post(_axis(0, 1.0))
        self.engine._process_events()
        scene.do_update(0.5)
        after = scene.world.component_for_entity(scene.player, CTransform).pos
        self.assertNotEqual(before, after)

    def test_button_does_not_crash_in_any_scene(self) -> None:
        for name in ("TITLE", "PLAY"):
            self.engine._apply_scene_change(name)
            pygame.event.clear()
            pygame.event.post(_button(pygame.JOYBUTTONDOWN, 0))
            pygame.event.post(_button(pygame.JOYBUTTONUP, 0))
            self.engine._process_events()


if __name__ == "__main__":
    unittest.main()
