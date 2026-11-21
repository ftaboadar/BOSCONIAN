import random

import pygame

from src.ecs.systems.s_player import system_player_input
from src.engine.input.command import Phase
from src.engine.scenes.info_scene import InstructionsScene
from src.engine.scenes.play_scene import PlayScene
from src.engine.service_locator import ServiceLocator, color_from_cfg
from src.engine.sfx import play_music

DIRECTIONS = ("UP", "DOWN", "LEFT", "RIGHT")


class AttractScene(PlayScene):
    """Modo atractor: el nivel se juega solo tras un rato de inactividad. Cualquier tecla lo interrumpe."""

    cheat_allowed = False  # la demo no es del jugador: el modo trampa no la afecta
    keeps_progress = False  # ni usa ni altera el progreso de la partida del jugador

    def do_create(self) -> None:
        super().do_create()
        cfg = self.engine.cfg_menu["attract"]
        self.clock.blast_left = 0.0  # la demo arranca sin cuenta
        self.elapsed = 0.0
        self.since_turn = 0.0
        self.cfg = cfg
        self.hint = ServiceLocator.fonts.get("main").render(
            cfg["hint"], False, color_from_cfg(self.engine.cfg_menu["colors"]["selected"]))

    def play_level_music(self, level: dict) -> None:
        """La demo va en silencio, como antes de la música por nivel."""
        play_music(None)

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
            # La demo "pulsa" una tecla por el jugador (y suelta las demás), con el mismo
            # sistema de input que la partida. Si la nave ya murió, no hay a quién llegarle.
            key = random.choice(DIRECTIONS)
            for direction in DIRECTIONS:
                system_player_input(self.world, direction,
                                    Phase.START if direction == key else Phase.END, True, False)
        super().do_update(delta_time)

    def do_draw(self, screen: pygame.Surface) -> None:
        super().do_draw(screen)
        screen.blit(self.hint, self.hint.get_rect(
            center=(self.engine.viewport.centerx,
                    self.engine.viewport.bottom - self.cfg["hint_bottom"])))


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
