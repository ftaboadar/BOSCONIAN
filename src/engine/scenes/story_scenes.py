"""Escenas de historia dirigidas por datos, como el arranque del Bosconian original: la pantalla
inicial, el logo que entra sobre el verde, los créditos y la cinemática antes de cada nivel. Su
línea de tiempo vive en assets/cfg/story.json."""

import pygame

from src.create.prefab_creator import create_stars
from src.ecs.systems.s_rendering import system_rendering
from src.ecs.systems.s_star import system_star_blink, system_star_fall, system_star_rendering
from src.engine.data_loader import load_level, load_story
from src.engine.game_state import BlankState
from src.engine.input.command import Phase
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator, color_from_cfg
from src.engine.timeline import Timeline


class StoryScene(Scene):
    """Reproduce la línea de tiempo de una sección de story.json.

    Cada evento aparece en su momento (`at`). Cualquier tecla la salta (pasada una breve gracia,
    para no saltarla con la tecla con la que se llegó), y al terminar o saltarla se pasa a la
    escena `next` (o a `skip_to`, si la sección lo indica). Opciones de la sección: `background`
    (color de fondo; sin él, negro), `stars` (false para no dibujar estrellas), `hud_zero` (la
    barra lateral en ceros, como antes de cargar) y `hud_lives` (mostrar las vidas)."""

    CFG_KEY = ""

    def do_create(self) -> None:
        story = load_story()
        self.cfg = story[self.CFG_KEY]
        self.grace = story["grace_seconds"]
        self.area = self.engine.viewport  # el campo de juego; a su derecha va la barra lateral
        self.stars = self.cfg.get("stars", True)
        if self.stars:
            create_stars(self.world, self.engine.cfg_world, self.area)
        self.background = color_from_cfg(self.cfg["background"]) if "background" in self.cfg else None
        self.panel_lives = self.cfg.get("hud_lives", False)
        self.timeline = Timeline(self.world, self.cfg["events"], self.engine.cfg_menu["colors"],
                                 self.fields())
        self.elapsed = 0.0
        if "music" in self.cfg:
            ServiceLocator.music.play(self.cfg["music"])

    def fields(self) -> dict:
        """Valores que los textos pueden usar entre llaves, por ejemplo {level}."""
        return {}

    def panel_state(self):
        return BlankState if self.cfg.get("hud_zero") else self.engine.state

    def finish(self) -> None:
        self.engine.switch_scene(self.cfg["next"])

    def do_action(self, action: str, phase: Phase) -> None:
        pass  # cualquier tecla (también las de acción) se maneja en do_any_key

    def do_any_key(self) -> None:
        if self.elapsed >= self.grace:
            self.engine.switch_scene(self.cfg.get("skip_to", self.cfg["next"]))

    def do_update(self, delta_time: float) -> None:
        self.elapsed += delta_time
        self.timeline.update(delta_time)
        if self.stars:
            system_star_blink(self.world, delta_time)
            system_star_fall(self.world, self.area, self.cfg["stars_speed"], delta_time)
        if self.elapsed >= self.cfg["duration"]:
            self.finish()

    def do_draw(self, screen: pygame.Surface) -> None:
        if self.background is not None:
            screen.fill(self.background, self.engine.viewport)
        if self.stars:
            system_star_rendering(self.world, screen)
        system_rendering(self.world, screen)


class SplashScene(StoryScene):
    """Lo primero que se ve: la música ya suena, la barra lateral aparece en ceros y en el centro,
    sobre las estrellas, unas líneas de texto (como «NAMCO VIDEO GAME COLLECTION» del original)."""

    CFG_KEY = "splash"


class LogoSlideScene(StoryScene):
    """Fondo verde menta por el que entra el logo del juego."""

    CFG_KEY = "logo_slide"


class BylineScene(StoryScene):
    """El logo sobre negro con los créditos: «ARRANGED BY» y los usuarios de GitHub del equipo."""

    CFG_KEY = "byline"


class CutsceneScene(StoryScene):
    """Cinemática antes de cada partida, como la del original: la nave grande y, en azul,
    «LEVEL n» y el nombre del nivel."""

    CFG_KEY = "cutscene"

    def fields(self) -> dict:
        level = load_level(self.engine.level)
        return {"level": self.engine.level, "round": level["round"], "subtitle": level.get("subtitle", "")}
