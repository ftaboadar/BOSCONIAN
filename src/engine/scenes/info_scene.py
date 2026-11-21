import pygame

from src.create.prefab_creator import create_stars
from src.ecs.systems.s_star import system_star_blink, system_star_fall, system_star_rendering
from src.engine.input.command import Phase
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator, color_from_cfg


def page_surfaces(cfg_menu: dict, page: dict) -> list[tuple[pygame.Surface, int]]:
    """Título y líneas de una página de menu.json, cada una con la altura a la que se dibuja."""
    font = ServiceLocator.fonts.get("main")
    layout = cfg_menu["page"]
    white = color_from_cfg(cfg_menu["colors"]["normal"])
    lines = [(font.render(page["title"], False, color_from_cfg(cfg_menu["colors"]["title"])),
              layout["title_y"])]
    for i, text in enumerate(page["lines"]):
        lines.append((font.render(text, False, white),
                      layout["lines_top"] + i * cfg_menu["line_height"]))
    return lines


def draw_page(screen: pygame.Surface, viewport: pygame.Rect,
              lines: list[tuple[pygame.Surface, int]], hint: pygame.Surface,
              hint_bottom: int) -> None:
    """Dibuja la página y, a `hint_bottom` px del borde de abajo, la ayuda para salir."""
    for surf, y in lines:
        screen.blit(surf, surf.get_rect(center=(viewport.centerx, viewport.top + y)))
    screen.blit(hint, hint.get_rect(center=(viewport.centerx, viewport.bottom - hint_bottom)))


class InfoScene(Scene):
    """Página de texto del menú. Las subclases fijan la sección de menu.json que muestran."""

    CFG_KEY = ""

    def do_create(self) -> None:
        self.area = self.engine.viewport  # el campo de juego; a su derecha va la barra lateral
        create_stars(self.world, self.engine.cfg_world, self.area)
        cfg = self.engine.cfg_menu
        self.lines = page_surfaces(cfg, self.page())
        self.hint = ServiceLocator.fonts.get("main").render(
            self.hint_text(), False, color_from_cfg(cfg["colors"]["selected"]))

    def page(self) -> dict:
        """Título y líneas de la página; las subclases pueden añadir datos de la partida."""
        return self.engine.cfg_menu[self.CFG_KEY]

    def hint_text(self) -> str:
        return self.engine.cfg_menu["page"]["hint"]

    def do_action(self, action: str, phase: Phase) -> None:
        if phase == Phase.START and action in ("SELECT", "BACK"):
            self.engine.switch_scene("TITLE")

    def do_update(self, delta_time: float) -> None:
        system_star_blink(self.world, delta_time)
        system_star_fall(self.world, self.area, self.engine.cfg_world["stars_menu_speed"], delta_time)

    def do_draw(self, screen: pygame.Surface) -> None:
        system_star_rendering(self.world, screen)
        draw_page(screen, self.engine.viewport, self.lines, self.hint,
                  self.engine.cfg_menu["page"]["hint_bottom"])


class InstructionsScene(InfoScene):
    CFG_KEY = "instructions"


class CreditsScene(InfoScene):
    CFG_KEY = "credits"
