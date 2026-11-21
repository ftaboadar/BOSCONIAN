"""Escenas de historia dirigidas por datos: intro animado antes del título (#35) y cutscene
antes de empezar a jugar (#37). Su línea de tiempo vive en assets/cfg/story.json."""

import pygame

from src.create.prefab_story import create_story_actor
from src.ecs.systems.s_animation import system_animation
from src.ecs.systems.s_arrival import system_arrival
from src.ecs.systems.s_destroy import system_destroy
from src.ecs.systems.s_lifetime import system_lifetime
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_rendering import system_rendering
from src.ecs.systems.s_star import system_star_blink, system_star_fall, system_star_rendering
from src.create.prefab_creator import create_stars
from src.engine.data_loader import load_level, load_story
from src.engine.input.command import Phase
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator
from src.engine.sfx import play_sound


class StoryScene(Scene):
    """Reproduce la línea de tiempo de una sección de story.json sobre un fondo de estrellas.

    Cada evento aparece en su momento (`at`). Cualquier tecla la salta (pasada una breve
    gracia, para no saltarla con la tecla con la que se llegó), y al terminar o saltarla se
    pasa a la escena `next`."""

    CFG_KEY = ""

    def do_create(self) -> None:
        story = load_story()
        self.cfg = story[self.CFG_KEY]
        self.grace = story["grace_seconds"]
        self.area = self.engine.screen.get_rect()
        create_stars(self.world, self.engine.cfg_world, self.area)
        self.pending = sorted(self.cfg["events"], key=lambda e: e["at"])  # estable: respeta el orden
        self.elapsed = 0.0
        if "music" in self.cfg:
            ServiceLocator.music.play(self.cfg["music"])

    def fields(self) -> dict:
        """Valores que los textos pueden usar entre llaves, por ejemplo {round}."""
        return {}

    def finish(self) -> None:
        self.engine.switch_scene(self.cfg["next"])

    def _fire(self, event: dict) -> None:
        if event["type"] == "sound":
            play_sound(event["sound"])
        else:
            create_story_actor(self.world, event, self.engine.cfg_menu["colors"], self.fields())

    def do_action(self, action: str, phase: Phase) -> None:
        pass  # cualquier tecla (también las de acción) se maneja en do_any_key

    def do_any_key(self) -> None:
        if self.elapsed >= self.grace:
            self.finish()

    def do_update(self, delta_time: float) -> None:
        self.elapsed += delta_time
        while self.pending and self.pending[0]["at"] <= self.elapsed:
            self._fire(self.pending.pop(0))
        system_lifetime(self.world, delta_time)
        system_movement(self.world, delta_time)
        system_arrival(self.world, delta_time)
        system_animation(self.world, delta_time)
        system_destroy(self.world)
        system_star_blink(self.world, delta_time)
        system_star_fall(self.world, self.area, self.cfg["stars_speed"], delta_time)
        if self.elapsed >= self.cfg["duration"]:
            self.finish()

    def do_draw(self, screen: pygame.Surface) -> None:
        system_star_rendering(self.world, screen)
        system_rendering(self.world, screen)


class IntroScene(StoryScene):
    """Intro animado al abrir el juego; tras él viene el título. Se salta con cualquier tecla."""

    CFG_KEY = "intro"


class CutsceneScene(StoryScene):
    """Cutscene al empezar una partida: anuncia la ronda y la nave despega hacia el nivel."""

    CFG_KEY = "cutscene"

    def fields(self) -> dict:
        return {"round": load_level(self.engine.level)["round"]}
