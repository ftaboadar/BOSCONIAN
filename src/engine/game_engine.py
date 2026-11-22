"""Motor del juego: game loop, escenas, input y servicios."""

import asyncio

import esper
import pygame

from src.create.prefab_ui import create_hud, create_shutter
from src.ecs.components.c_hud import CHud
from src.ecs.components.c_shutter import CShutter, ShutterState
from src.ecs.systems.s_hud import system_cheat_rendering, system_hud_rendering
from src.ecs.systems.s_shutter import shutter_start, system_shutter, system_shutter_rendering
from src.engine.data_loader import load_json, load_resources
from src.engine.game_state import GameState
from src.engine.input.command import CommandMap
from src.engine.scenes.attract_scene import AttractInstructionsScene, AttractScene
from src.engine.scenes.editor_scene import EditorScene
from src.engine.scenes.end_scenes import DefeatScene, RecordScene, VictoryScene
from src.engine.scenes.info_scene import CreditsScene, InstructionsScene
from src.engine.scenes.play_scene import PlayScene
from src.engine.scenes.scene import Scene
from src.engine.scenes.story_scenes import BylineScene, CutsceneScene, LogoSlideScene, SplashScene
from src.engine.scenes.title_scene import TitleScene
from src.engine.service_locator import ServiceLocator, color_from_cfg, rect_from_cfg


class GameEngine:
    SCENES = {"TITLE": TitleScene, "PLAY": PlayScene,
              "INSTRUCTIONS": InstructionsScene, "CREDITS": CreditsScene,
              "ATTRACT": AttractScene, "ATTRACT_INFO": AttractInstructionsScene,
              "SPLASH": SplashScene, "LOGO_SLIDE": LogoSlideScene, "BYLINE": BylineScene,
              "CUTSCENE": CutsceneScene, "EDITOR": EditorScene,
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
        cfg_input = load_json("assets/cfg/input.json")
        self.commands = CommandMap(cfg_input["keyboard"], cfg_input.get("gamepad"))
        self._gamepads: dict[int, pygame.joystick.JoystickType] = {}
        self._open_connected_gamepads()
        self.cfg_scenes = load_json("assets/cfg/scenes.json")
        self.cfg_world = load_json("assets/cfg/world.json")
        self.cfg_menu = load_json("assets/cfg/menu.json")
        self.state = GameState()  # vidas, puntaje, récord y nivel, compartido entre escenas
        life_icon = ServiceLocator.images.get("ships").subsurface(
            rect_from_cfg(load_json("assets/cfg/player.json")["sprite_rect"])).copy()
        self.viewport = rect_from_cfg(self.cfg_world["viewport"])  # el campo de juego
        # La barra lateral ocupa el resto de la pantalla, a la derecha del campo de juego.
        self.panel = pygame.Rect(self.viewport.right, 0, cfg_window["size"]["w"] - self.viewport.right,
                                 cfg_window["size"]["h"])
        # La barra y la persiana son las mismas en todas las pantallas: viven en un mundo ECS
        # del motor, aparte del de cada escena.
        self.ui_world = esper.World()
        self.hud = self.ui_world.component_for_entity(
            create_hud(self.ui_world, load_json("assets/cfg/hud.json"),
                       ServiceLocator.fonts.get("main"), life_icon,
                       self.state.cfg["life_icons_max"], self.panel), CHud)
        self.shutter = self.ui_world.component_for_entity(
            create_shutter(self.ui_world, self.cfg_world["shutter"], self.viewport), CShutter)
        self.world_size = pygame.Vector2(self.cfg_world["world_size"]["w"],
                                         self.cfg_world["world_size"]["h"])

        self.clock = pygame.time.Clock()
        self.delta_time = 0.0
        self.is_running = False
        self._current_scene: Scene | None = None
        self._next_scene: str | None = None

    def run(self) -> None:
        asyncio.run(self.run_async())

    async def run_async(self) -> None:
        """Game loop. Es una corrutina para la versión web (pygbag): tras cada fotograma cede
        el control al navegador; en escritorio ese `sleep(0)` no espera nada."""
        self.is_running = True
        self._apply_scene_change(self.cfg_scenes["start_scene"])
        while self.is_running:
            self._calculate_time()
            self._frame()
            await asyncio.sleep(0)
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
        if shutter_start(self.ui_world, name):
            self._next_scene = None  # la escena actual queda congelada hasta cubrir el campo
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

    def _open_connected_gamepads(self) -> None:
        for index in range(pygame.joystick.get_count()):
            self._open_gamepad(index)

    def _open_gamepad(self, device_index: int) -> None:
        """pygame solo emite eventos de un gamepad después de abrirlo y de guardar la referencia."""
        try:
            pad = pygame.joystick.Joystick(device_index)
        except pygame.error:
            return
        self._gamepads[pad.get_instance_id()] = pad

    def _process_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
                continue
            if event.type == pygame.JOYDEVICEADDED:
                self._open_gamepad(event.device_index)  # conectar en caliente
            elif event.type == pygame.JOYDEVICEREMOVED:
                self._gamepads.pop(event.instance_id, None)
            if self.shutter.state == ShutterState.CLOSING:
                if event.type == pygame.JOYDEVICEREMOVED:
                    self.commands.translate(event)  # suelta direcciones aunque la persiana cierre
                continue  # sin teclas mientras la persiana se cierra
            if event.type in (pygame.KEYDOWN, pygame.JOYBUTTONDOWN):
                self._current_scene.do_any_key()
            for command in self.commands.translate(event):
                self._current_scene.do_action(*command)

    def _update(self) -> None:
        closing = self.shutter.state == ShutterState.CLOSING
        covered_for = system_shutter(self.ui_world, self.delta_time)
        if covered_for is not None:  # el campo ya está cubierto: se cambia de escena
            self._apply_scene_change(covered_for)
        if closing:
            return  # mientras se cierra, la escena actual no avanza
        self._current_scene.do_update(self.delta_time)

    def _draw(self) -> None:
        scene = self._current_scene
        self.screen.fill(self.bg_color)
        scene.do_draw(self.screen)
        self.screen.set_clip(None)
        system_shutter_rendering(self.ui_world, self.screen)  # sobre el campo de juego; la barra se dibuja después y no se mueve
        if scene.has_panel:
            self._draw_panel(scene)
        pygame.display.flip()

    def _draw_panel(self, scene: Scene) -> None:
        """La barra lateral, igual en todas las pantallas del juego (salvo el editor)."""
        self.screen.set_clip(None)
        self.screen.fill(self.bg_color, self.panel)  # tapa lo que la escena haya dibujado de más
        scene.draw_radar(self.screen)
        system_hud_rendering(self.ui_world, self.screen, scene.panel_state(), scene.panel_round(),
                             scene.panel_lives)
        system_cheat_rendering(self.ui_world, self.screen, self.state.cheat)

    def _clean(self) -> None:
        if self._current_scene is not None:
            self._current_scene.do_clean()
        pygame.quit()
