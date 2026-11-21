"""Motor del juego: game loop, escenas, input y servicios."""

import pygame

from src.engine.data_loader import load_json, load_resources
from src.engine.game_state import GameState
from src.engine.hud import Hud
from src.engine.shutter import Shutter
from src.engine.input.command import CommandMap
from src.engine.scenes.attract_scene import AttractInstructionsScene, AttractScene
from src.engine.scenes.editor_scene import EditorScene
from src.engine.scenes.end_scenes import DefeatScene, RecordScene, VictoryScene
from src.engine.scenes.info_scene import CreditsScene, InstructionsScene
from src.engine.scenes.play_scene import PlayScene
from src.engine.scenes.scene import Scene
from src.engine.scenes.story_scenes import CutsceneScene, IntroScene
from src.engine.scenes.title_scene import TitleScene
from src.engine.service_locator import ServiceLocator, color_from_cfg


class GameEngine:
    SCENES = {"TITLE": TitleScene, "PLAY": PlayScene,
              "INSTRUCTIONS": InstructionsScene, "CREDITS": CreditsScene,
              "ATTRACT": AttractScene, "ATTRACT_INFO": AttractInstructionsScene,
              "INTRO": IntroScene, "CUTSCENE": CutsceneScene, "EDITOR": EditorScene,
              "VICTORY": VictoryScene, "DEFEAT": DefeatScene, "RECORD": RecordScene}

    def __init__(self) -> None:
        pygame.init()
        cfg_window = load_json("assets/cfg/window.json")
        self.bg_color = color_from_cfg(cfg_window["bg_color"])
        self.framerate = cfg_window["framerate"]
        self.screen = pygame.display.set_mode(
            (cfg_window["size"]["w"], cfg_window["size"]["h"]), pygame.SCALED)
        pygame.display.set_caption(cfg_window["title"])

        ServiceLocator.init(load_resources())
        self.commands = CommandMap(load_json("assets/cfg/input.json")["keyboard"])
        self.cfg_scenes = load_json("assets/cfg/scenes.json")
        self.cfg_world = load_json("assets/cfg/world.json")
        self.cfg_menu = load_json("assets/cfg/menu.json")
        self.state = GameState()  # vidas, puntaje, récord y nivel, compartido entre escenas
        r = load_json("assets/cfg/player.json")["sprite_rect"]
        life_icon = ServiceLocator.images.get("ships").subsurface(
            pygame.Rect(r["x"], r["y"], r["w"], r["h"])).copy()
        v = self.cfg_world["viewport"]
        self.viewport = pygame.Rect(v["x"], v["y"], v["w"], v["h"])  # el campo de juego
        # La barra lateral ocupa el resto de la pantalla, a la derecha del campo de juego.
        panel = pygame.Rect(self.viewport.right, 0, cfg_window["size"]["w"] - self.viewport.right,
                            cfg_window["size"]["h"])
        self.hud = Hud(ServiceLocator.fonts.get("main"), self.state.cfg["life_icons_max"], life_icon, panel)
        self.shutter = Shutter(self.cfg_world["shutter"], self.viewport)  # persiana entre pantallas
        self.world_size = pygame.Vector2(self.cfg_world["world_size"]["w"],
                                         self.cfg_world["world_size"]["h"])

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
            self._frame()
        self._clean()

    def _frame(self) -> None:
        """Un fotograma: teclas, lógica y dibujo; al final, el cambio de escena pedido."""
        self._process_events()
        self._update()
        self._draw()
        if self._next_scene is not None:
            self._request_scene(self._next_scene)

    def _request_scene(self, name: str) -> None:
        """Cambia de escena, con persiana si la escena de destino la pide (y no hay otra en curso)."""
        if self.shutter.wants(name) and not self.shutter.busy:
            self.shutter.close(name)  # la escena actual queda congelada hasta cubrir el campo
            self._next_scene = None
        else:
            self._apply_scene_change(name)

    @property
    def level(self) -> int:
        """Nivel actual; el menú del título lo elige y el flujo de niveles lo avanza."""
        return self.state.level

    @level.setter
    def level(self, value: int) -> None:
        self.state.level = value

    def start_game(self) -> None:
        """Nueva partida desde el nivel elegido en el título (conserva el récord)."""
        self.state.reset(self.state.level)

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
            if self.shutter.closing:
                continue  # sin teclas mientras la persiana se cierra
            if event.type == pygame.KEYDOWN:
                self._current_scene.do_any_key()
            command = self.commands.translate(event)
            if command is not None:
                self._current_scene.do_action(*command)

    def _update(self) -> None:
        if self.shutter.closing:
            if self.shutter.update(self.delta_time):  # el campo ya está cubierto: se cambia de escena
                self._apply_scene_change(self.shutter.target)
                self.shutter.open()
            return  # mientras se cierra, la escena actual no avanza
        self.shutter.update(self.delta_time)
        self._current_scene.do_update(self.delta_time)

    def _draw(self) -> None:
        scene = self._current_scene
        self.screen.fill(self.bg_color)
        scene.do_draw(self.screen)
        self.screen.set_clip(None)
        self.shutter.draw(self.screen)  # sobre el campo de juego; la barra se dibuja después y no se mueve
        if scene.has_panel:
            self._draw_panel(scene)
        pygame.display.flip()

    def _draw_panel(self, scene: Scene) -> None:
        """La barra lateral, igual en todas las pantallas del juego (salvo el editor)."""
        self.screen.set_clip(None)
        panel = pygame.Rect(self.viewport.right, 0, self.screen.get_width() - self.viewport.right,
                            self.screen.get_height())
        self.screen.fill(self.bg_color, panel)  # tapa lo que la escena haya dibujado de más
        scene.draw_radar(self.screen)
        self.hud.draw(self.screen, self.state, scene.panel_round())
        self.hud.draw_cheat(self.screen, self.state)

    def _clean(self) -> None:
        if self._current_scene is not None:
            self._current_scene.do_clean()
        pygame.quit()
