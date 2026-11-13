"""Motor del juego: game loop, escenas, input y servicios."""

import pygame

from src.engine.input.command import CommandMap
from src.engine.scenes.play_scene import PlayScene
from src.engine.scenes.scene import Scene
from src.engine.scenes.title_scene import TitleScene
from src.engine.service_locator import ServiceLocator, load_json


class GameEngine:
    SCENES = {"TITLE": TitleScene, "PLAY": PlayScene}

    def __init__(self) -> None:
        pygame.init()
        cfg_window = load_json("assets/cfg/window.json")
        bg = cfg_window["bg_color"]
        self.bg_color = pygame.Color(bg["r"], bg["g"], bg["b"])
        self.framerate = cfg_window["framerate"]
        self.screen = pygame.display.set_mode(
            (cfg_window["size"]["w"], cfg_window["size"]["h"]), pygame.SCALED)
        pygame.display.set_caption(cfg_window["title"])

        ServiceLocator.init(load_json("assets/cfg/resources.json"))
        self.commands = CommandMap(load_json("assets/cfg/input.json")["keyboard"])
        self.cfg_scenes = load_json("assets/cfg/scenes.json")
        self.cfg_world = load_json("assets/cfg/world.json")
        self.world_size = pygame.Vector2(self.cfg_world["world_size"]["w"],
                                         self.cfg_world["world_size"]["h"])
        v = self.cfg_world["viewport"]
        self.viewport = pygame.Rect(v["x"], v["y"], v["w"], v["h"])

        self.clock = pygame.time.Clock()
        self.delta_time = 0.0
        self.is_running = False
        self._current_scene: Scene | None = None
        self._next_scene: str | None = None

    def run(self) -> None:
        self.is_running = True
        self._apply_scene_change(self.cfg_scenes["start_scene"])
        while self.is_running:
            self._calculate_time()
            self._process_events()
            self._update()
            self._draw()
            if self._next_scene is not None:
                self._apply_scene_change(self._next_scene)
        self._clean()

    def switch_scene(self, name: str) -> None:
        """Solicita cambiar de escena al final del frame actual."""
        self._next_scene = name

    def quit(self) -> None:
        self.is_running = False

    def _apply_scene_change(self, name: str) -> None:
        if self._current_scene is not None:
            self._current_scene.do_clean()
        self._current_scene = self.SCENES[name](self)
        self._current_scene.do_create()
        self._next_scene = None

    def _calculate_time(self) -> None:
        self.clock.tick(self.framerate)
        self.delta_time = self.clock.get_time() / 1000.0

    def _process_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
                continue
            command = self.commands.translate(event)
            if command is not None:
                self._current_scene.do_action(*command)

    def _update(self) -> None:
        self._current_scene.do_update(self.delta_time)

    def _draw(self) -> None:
        self.screen.fill(self.bg_color)
        self._current_scene.do_draw(self.screen)
        pygame.display.flip()

    def _clean(self) -> None:
        if self._current_scene is not None:
            self._current_scene.do_clean()
        pygame.quit()
