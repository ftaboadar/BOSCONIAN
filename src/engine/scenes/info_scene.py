import pygame

from src.create.prefab_creator import create_stars
from src.ecs.systems.s_star import system_star_blink, system_star_fall, system_star_rendering
from src.engine.input.command import Phase
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator, color_from_cfg


class InfoScene(Scene):
    """Página de texto del menú. Las subclases fijan la sección de menu.json que muestran."""

    CFG_KEY = ""
    HINT = "ENTER: VOLVER"

    def do_create(self) -> None:
        self.area = self.engine.screen.get_rect()
        create_stars(self.world, self.engine.cfg_world, self.area)
        cfg = self.engine.cfg_menu
        page = cfg[self.CFG_KEY]
        font = ServiceLocator.fonts.get("main")
        white = color_from_cfg(cfg["colors"]["normal"])
        self.lines: list[tuple[pygame.Surface, int]] = []
        self.lines.append((font.render(page["title"], False, color_from_cfg(cfg["colors"]["title"])), 24))
        for i, text in enumerate(page["lines"]):
            self.lines.append((font.render(text, False, white), 52 + i * cfg["line_height"]))
        self.hint = font.render(self.hint_text(), False, color_from_cfg(cfg["colors"]["selected"]))

    def hint_text(self) -> str:
        return self.HINT

    def do_action(self, action: str, phase: Phase) -> None:
        if phase == Phase.START and action in ("SELECT", "BACK"):
            self.engine.switch_scene("TITLE")

    def do_update(self, delta_time: float) -> None:
        system_star_blink(self.world, delta_time)
        system_star_fall(self.world, self.area, self.engine.cfg_world["stars_menu_speed"], delta_time)

    def do_draw(self, screen: pygame.Surface) -> None:
        system_star_rendering(self.world, screen)
        cx = screen.get_width() // 2
        for surf, y in self.lines:
            screen.blit(surf, surf.get_rect(center=(cx, y)))
        screen.blit(self.hint, self.hint.get_rect(center=(cx, screen.get_height() - 16)))


class InstructionsScene(InfoScene):
    CFG_KEY = "instructions"


class CreditsScene(InfoScene):
    CFG_KEY = "credits"
