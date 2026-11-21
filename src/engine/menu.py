"""Menú vertical reutilizable (título, pausa, victoria y derrota)."""

import pygame

from src.engine.input.command import Phase
from src.engine.service_locator import ServiceLocator, color_from_cfg
from src.engine.sfx import play_sound


class Menu:
    """Lista de opciones navegable con arriba/abajo; SELECT devuelve la acción elegida."""

    def __init__(self, items: list[dict], colors: dict, line_height: int) -> None:
        self.items = [dict(item) for item in items]
        self.line_height = line_height
        self.normal = color_from_cfg(colors["normal"])
        self.selected_color = color_from_cfg(colors["selected"])
        self.selected = 0

    @property
    def current_action(self) -> str:
        return self.items[self.selected]["action"]

    def set_label(self, action: str, label: str) -> None:
        for item in self.items:
            if item["action"] == action:
                item["label"] = label

    def handle_action(self, action: str, phase: Phase) -> str | None:
        """Mueve la selección o devuelve la acción de la opción elegida."""
        if phase != Phase.START:
            return None
        if action == "UP":
            self.selected = (self.selected - 1) % len(self.items)
            play_sound("menu_select")
        elif action == "DOWN":
            self.selected = (self.selected + 1) % len(self.items)
            play_sound("menu_select")
        elif action == "SELECT":
            play_sound("menu_select")
            return self.current_action
        return None

    def draw(self, screen: pygame.Surface, center_x: int, top: int) -> None:
        font = ServiceLocator.fonts.get("main")
        for i, item in enumerate(self.items):
            is_selected = i == self.selected
            text = f"> {item['label']}" if is_selected else item["label"]
            surf = font.render(text, False,
                               self.selected_color if is_selected else self.normal)
            screen.blit(surf, surf.get_rect(center=(center_x, top + i * self.line_height)))
