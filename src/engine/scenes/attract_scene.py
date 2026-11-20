import random

import pygame

from src.engine.input.command import Phase
from src.engine.scenes.info_scene import InstructionsScene
from src.engine.scenes.play_scene import PlayScene
from src.engine.service_locator import ServiceLocator

DIRECTIONS = ("UP", "DOWN", "LEFT", "RIGHT")


class AttractScene(PlayScene):
    """Modo atractor: el nivel se juega solo tras un rato de inactividad. Cualquier tecla lo interrumpe."""

    def do_create(self) -> None:
        super().do_create()
        cfg = self.engine.cfg_menu["attract"]
        self.blast_left = 0.0  # la demo arranca sin cuenta
        self.elapsed = 0.0
        self.since_turn = 0.0
        self.cfg = cfg
        self.hint = ServiceLocator.fonts.get("main").render(
            cfg["hint"], False, pygame.Color(255, 220, 0))

    def do_any_key(self) -> None:
        self.engine.switch_scene("TITLE")

    def do_action(self, action: str, phase: Phase) -> None:
        """El jugador no controla la demo."""

    def player_died(self) -> None:
        """En la demo la muerte no cuesta vidas: termina la demo y pasa a las instrucciones."""
        self.engine.switch_scene("ATTRACT_INFO")

    def do_update(self, delta_time: float) -> None:
        self.elapsed += delta_time
        if self.elapsed >= self.cfg["demo_seconds"]:
            self.engine.switch_scene("ATTRACT_INFO")  # tras la demo, las instrucciones
            return
        self.since_turn += delta_time
        if self.since_turn >= self.cfg["turn_every"]:
            self.since_turn = 0.0
            dirs = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
            self.direction = pygame.Vector2(dirs[random.choice(DIRECTIONS)])
        super().do_update(delta_time)

    def do_draw(self, screen: pygame.Surface) -> None:
        super().do_draw(screen)
        screen.blit(self.hint, self.hint.get_rect(
            center=(self.engine.viewport.centerx, self.engine.viewport.bottom - 8)))


class AttractInstructionsScene(InstructionsScene):
    """Instrucciones del modo atractor: vuelven al título solas o con cualquier tecla."""

    def hint_text(self) -> str:
        return self.engine.cfg_menu["attract"]["hint"]

    def do_create(self) -> None:
        super().do_create()
        self.elapsed = 0.0

    def do_any_key(self) -> None:
        self.engine.switch_scene("TITLE")

    def do_update(self, delta_time: float) -> None:
        super().do_update(delta_time)
        self.elapsed += delta_time
        if self.elapsed >= self.engine.cfg_menu["attract"]["instructions_seconds"]:
            self.engine.switch_scene("TITLE")
