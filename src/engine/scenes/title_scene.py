import pygame

from src.create.prefab_creator import create_stars
from src.ecs.components.c_arrival import CArrival
from src.ecs.components.c_surface import CSurface
from src.ecs.systems.s_rendering import system_rendering
from src.ecs.systems.s_star import system_star_blink, system_star_fall, system_star_rendering
from src.engine.data_loader import level_numbers, load_story
from src.engine.input.command import Phase
from src.engine.menu import Menu
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator, color_from_cfg
from src.engine.timeline import Timeline

# "Jugar" pasa por la cinemática del nivel, que al terminar o saltarse lleva al juego.
SCENE_BY_ACTION = {"PLAY": "CUTSCENE", "INSTRUCTIONS": "INSTRUCTIONS", "CREDITS": "CREDITS"}


class TitleScene(Scene):
    """Título sobre fondo verde con estrellas: el logo entra por la derecha, «PUSH BUTTON
    TO START» por la izquierda y parpadea. Al pulsar un botón aparece el menú (jugar, elegir
    nivel, instrucciones y créditos) sobre el mismo fondo. Sus eventos viven en story.json."""

    def do_create(self) -> None:
        stage = self.engine.viewport  # el campo de juego; a su derecha va la barra lateral
        self.area = stage
        cfg = self.engine.cfg_menu
        story = load_story()
        self.background = color_from_cfg(story["title"]["background"])
        # «PUSH BUTTON TO START» parpadea con este período una vez que llegó a su sitio.
        self.blink_seconds = story["title"]["push_blink_seconds"]
        create_stars(self.world, self.engine.cfg_world, stage)
        self.timeline = Timeline(self.world, story["title"]["events"], cfg["colors"])
        self.menu = Menu(cfg["title_items"], cfg["colors"], cfg["line_height"])
        self.menu_top = story["title"]["menu_top"]
        self.mode = "push"  # "push": esperando un botón; "menu": eligiendo
        self.idle = 0.0
        self.blink = 0.0
        self.grace = story["grace_seconds"]
        self.elapsed = 0.0
        self._pressed_now = False  # la tecla que abrió el menú no debe además elegir en él
        self._push_surfaces: dict[int, pygame.Surface] = {}
        self.levels = level_numbers() or [self.engine.level]
        self._refresh_level_label()
        ServiceLocator.music.play("title")

    def _refresh_level_label(self) -> None:
        self.menu.set_label(
            "LEVEL", self.engine.cfg_menu["level_label"].format(level=self.engine.level))

    def _cycle_level(self, step: int) -> None:
        index = self.levels.index(self.engine.level) if self.engine.level in self.levels else 0
        self.engine.level = self.levels[(index + step) % len(self.levels)]
        self._refresh_level_label()

    def _open_menu(self) -> None:
        self.timeline.remove_group("push")
        self._push_surfaces.clear()
        self.mode = "menu"
        self._pressed_now = True

    def do_action(self, action: str, phase: Phase) -> None:
        if phase != Phase.START or self.mode != "menu" or self._pressed_now:
            return
        if action == "FIRE":
            action = "SELECT"  # como en el original: disparar también elige (y empieza la partida)
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
        if self.mode == "push" and self.elapsed >= self.grace:
            self._open_menu()  # cualquier botón pasa del «PUSH BUTTON» al menú

    def do_update(self, delta_time: float) -> None:
        self._pressed_now = False
        self.elapsed += delta_time
        self.idle += delta_time
        if self.idle >= self.engine.cfg_menu["attract"]["idle_seconds"]:
            self.engine.switch_scene("ATTRACT")  # inactividad: arranca el modo atractor
        self.timeline.update(delta_time)
        system_star_blink(self.world, delta_time)
        system_star_fall(self.world, self.area, self.engine.cfg_world["stars_menu_speed"], delta_time)
        self._blink_push(delta_time)

    def _blink_push(self, delta_time: float) -> None:
        """Hace parpadear «PUSH BUTTON TO START» cuando ya llegó a su sitio."""
        if self.mode != "push":
            return
        self.blink += delta_time
        for ent in self.timeline.groups.get("push", []):
            if not self.world.entity_exists(ent):
                continue
            c_s = self.world.component_for_entity(ent, CSurface)
            self._push_surfaces.setdefault(ent, c_s.surf)
            arrived = not self.world.has_component(ent, CArrival)
            visible = (not arrived) or int(self.blink / self.blink_seconds) % 2 == 0
            c_s.surf = self._push_surfaces[ent] if visible else pygame.Surface((1, 1), pygame.SRCALPHA)

    def do_draw(self, screen: pygame.Surface) -> None:
        screen.fill(self.background, self.engine.viewport)
        system_star_rendering(self.world, screen)
        system_rendering(self.world, screen)
        if self.mode == "menu":
            self.menu.draw(screen, self.engine.viewport.centerx, self.menu_top)
