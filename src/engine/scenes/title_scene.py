import pygame

from src.create.prefab_creator import create_image, create_stars
from src.ecs.systems.s_rendering import system_rendering
from src.ecs.systems.s_star import system_star_blink, system_star_fall, system_star_rendering
from src.engine.data_loader import level_numbers
from src.engine.input.command import Phase
from src.engine.menu import Menu
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator

SCENE_BY_ACTION = {"PLAY": "PLAY", "INSTRUCTIONS": "INSTRUCTIONS", "CREDITS": "CREDITS"}


class TitleScene(Scene):
    """Título con menú: jugar, elegir nivel, instrucciones y créditos."""

    def do_create(self) -> None:
        w, h = self.engine.screen.get_size()
        self.area = self.engine.screen.get_rect()
        cfg = self.engine.cfg_menu
        create_stars(self.world, self.engine.cfg_world, self.area)
        create_image(self.world, "title", pygame.Vector2(w / 2, h * 0.35))
        self.menu = Menu(cfg["title_items"], cfg["colors"], cfg["line_height"])
        self.menu_top = int(h * 0.62)
        self.idle = 0.0
        self.levels = level_numbers() or [self.engine.level]
        self._refresh_level_label()
        ServiceLocator.music.play("title")

    def _refresh_level_label(self) -> None:
        self.menu.set_label("LEVEL", f"NIVEL < {self.engine.level} >")

    def _cycle_level(self, step: int) -> None:
        index = self.levels.index(self.engine.level) if self.engine.level in self.levels else 0
        self.engine.level = self.levels[(index + step) % len(self.levels)]
        self._refresh_level_label()

    def do_action(self, action: str, phase: Phase) -> None:
        if phase != Phase.START:
            return
        if self.menu.current_action == "LEVEL" and action in ("LEFT", "RIGHT"):
            self._cycle_level(-1 if action == "LEFT" else 1)
            return
        chosen = self.menu.handle_action(action, phase)
        if chosen == "PLAY":
            self.engine.start_game()
        if chosen in SCENE_BY_ACTION:
            self.engine.switch_scene(SCENE_BY_ACTION[chosen])

    def do_any_key(self) -> None:
        self.idle = 0.0

    def do_update(self, delta_time: float) -> None:
        self.idle += delta_time
        if self.idle >= self.engine.cfg_menu["attract"]["idle_seconds"]:
            self.engine.switch_scene("ATTRACT")  # inactividad: arranca el modo atractor
        system_star_blink(self.world, delta_time)
        system_star_fall(self.world, self.area, self.engine.cfg_world["stars_menu_speed"], delta_time)

    def do_draw(self, screen: pygame.Surface) -> None:
        system_star_rendering(self.world, screen)
        system_rendering(self.world, screen)
        self.menu.draw(screen, screen.get_width() // 2, self.menu_top)
