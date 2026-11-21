"""Escenas de fin de partida: victoria (#31), derrota con continuar (#32) y felicitación por récord (#43)."""

import math

import pygame

from src.engine.input.command import Phase
from src.engine.level_flow import after_game_end
from src.engine.sfx import play_music, play_sound
from src.engine.scenes.info_scene import InfoScene
from src.engine.service_locator import ServiceLocator, color_from_cfg

class _EndScene(InfoScene):
    """Página de fin de partida: a sus líneas les siguen las cifras de la partida (`stats` en
    menu.json, con campos de GameState entre llaves)."""

    def hint_text(self) -> str:
        return self.engine.cfg_menu["end_hint"]

    def do_create(self) -> None:
        super().do_create()
        # Cada final tiene su música (menu.json); sin ella, silencio: la del nivel no sigue.
        play_music(self.engine.cfg_menu[self.CFG_KEY].get("music"))
        # Evita saltarse la escena con la tecla que se pulsaba al terminar el juego.
        self.grace = self.engine.cfg_menu["end_grace_seconds"]

    def page(self) -> dict:
        base = self.engine.cfg_menu[self.CFG_KEY]
        s = self.engine.state
        fields = {"score": s.score, "hi_score": s.hi_score, "lives_used": s.lives_used,
                  "continues_used": s.continues_used}
        stats = [text.format(**fields) for text in base["stats"]]
        return {"title": base["title"], "lines": base["lines"] + [""] + stats}


class VictoryScene(_EndScene):
    """Tras el último nivel: muestra vidas y continuaciones usadas; cualquier tecla vuelve al título."""

    CFG_KEY = "victory"

    def do_create(self) -> None:
        super().do_create()
        self.elapsed = 0.0

    def do_update(self, delta_time: float) -> None:
        self.elapsed += delta_time
        super().do_update(delta_time)

    def do_action(self, action: str, phase: Phase) -> None:
        pass  # cualquier tecla se maneja en do_any_key

    def do_any_key(self) -> None:
        if self.elapsed >= self.grace:
            self.engine.switch_scene(after_game_end(self.engine.state))


class RecordScene(VictoryScene):
    """Felicitación al terminar una partida (victoria o derrota) en la que se superó el HI-SCORE.

    Muestra el nuevo récord; cualquier tecla vuelve al título."""

    CFG_KEY = "record"

    def do_create(self) -> None:
        super().do_create()
        play_sound("extra_life")

    def do_any_key(self) -> None:
        if self.elapsed >= self.grace:
            self.engine.switch_scene("TITLE")


class DefeatScene(_EndScene):
    """Sin vidas: ENTER continúa en el mismo nivel durante unos segundos; si no, vuelve al título."""

    CFG_KEY = "defeat"

    def do_create(self) -> None:
        super().do_create()
        self.remaining = float(self.engine.state.cfg["continue_seconds"])
        cfg = self.engine.cfg_menu
        self.cfg_defeat = cfg[self.CFG_KEY]
        self.font = ServiceLocator.fonts.get("main")
        self.color = color_from_cfg(cfg["colors"]["selected"])
        self.hint = self.font.render("", False, self.color)  # la cuenta se dibuja cada frame

    def do_action(self, action: str, phase: Phase) -> None:
        if phase != Phase.START:
            return
        if action == "SELECT":
            self.engine.state.continue_game()  # recupera las vidas, pierde el puntaje
            self.engine.switch_scene("PLAY")  # mismo nivel: state.level no cambia
        elif action == "BACK":
            self.engine.switch_scene(after_game_end(self.engine.state))

    def do_update(self, delta_time: float) -> None:
        self.remaining -= delta_time
        if self.remaining <= 0:
            self.engine.switch_scene(after_game_end(self.engine.state))
        super().do_update(delta_time)

    def do_draw(self, screen: pygame.Surface) -> None:
        super().do_draw(screen)
        seconds = max(0, math.ceil(self.remaining))
        text = self.font.render(self.cfg_defeat["continue_text"].format(seconds=seconds), False,
                                self.color)
        stage = self.engine.viewport
        screen.blit(text, text.get_rect(
            center=(stage.centerx, stage.bottom - self.cfg_defeat["continue_bottom"])))
