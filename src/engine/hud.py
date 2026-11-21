"""HUD fijo: se dibuja en pantalla, sin pasar por la cámara. Lee todo del GameState.

La distribución sale de medir el Bosconian original (X68000): una barra de 64 px a la derecha
del campo de juego de 192 px. De arriba abajo: HI-SCORE (rojo) y su valor a la derecha, 1UP a
la izquierda y su valor a la derecha, CONDITION con una barra de color a todo el ancho, el radar
(lo dibuja s_minimap), las vidas como mini-naves y ROUND pegado al borde de abajo."""

import pygame

from src.engine.data_loader import load_entity_cfg
from src.engine.game_state import GameState
from src.engine.service_locator import color_from_cfg

# Textos, colores y posiciones salen de assets/cfg/hud.json.
CFG = load_entity_cfg("hud", ("texts", "colors", "rows", "condition_bar", "life_icons",
                              "letter_gap", "trimmed_letters"))
TEXTS = CFG["texts"]
WHITE = color_from_cfg(CFG["colors"]["text"])
RED = color_from_cfg(CFG["colors"]["highlight"])
BLACK = color_from_cfg(CFG["colors"]["bar_text"])
# Color de la barra de CONDITION para cada alerta (texto negro encima).
CONDITION_COLORS = {name: color_from_cfg(c) for name, c in CFG["colors"]["condition"].items()}
# CONDITION tiene 9 letras de 7 px y debe caber en 64 px. Para que no se toquen, cada letra se
# recorta a su tinta y se separa 1 px; a la I se le quita 1 px de cada remate: 56 px + 8 huecos = 64.
LETTER_GAP = CFG["letter_gap"]
TRIMMED = CFG["trimmed_letters"]  # letra -> columnas que pierde por cada lado
ROWS = CFG["rows"]
BAR_Y, BAR_H = CFG["condition_bar"]["y"], CFG["condition_bar"]["h"]
ICONS_Y = CFG["life_icons"]["y"]  # justo bajo el radar
ICON_SPACING = CFG["life_icons"]["spacing"]  # 4 mini-naves llenan justo los 64 px de la barra


class Hud:
    def __init__(self, font: pygame.font.Font, icons_max: int, icon: pygame.Surface,
                 panel: pygame.Rect) -> None:
        self.font = font
        self.icons_max = icons_max
        self.icon = icon  # la nave del jugador, mirando hacia arriba
        self.panel = panel  # la barra: a la derecha del campo de juego

    def _text(self, screen: pygame.Surface, text: str, color: pygame.Color, y: int,
              align: str = "left") -> None:
        surf = self.font.render(text, False, color)
        x = {"left": self.panel.left, "right": self.panel.right - surf.get_width(),
             "center": self.panel.centerx - surf.get_width() // 2}[align]
        screen.blit(surf, (x, y))

    def _text_tight(self, screen: pygame.Surface, text: str, color: pygame.Color, y: int) -> None:
        """Texto con las letras más juntas, para que quepa en el ancho de la barra."""
        x = self.panel.left
        for char in text:
            glyph = self.font.render(char, False, color)
            ink = glyph.get_bounding_rect()
            trim = TRIMMED.get(char, 0)
            area = pygame.Rect(ink.left + trim, 0, ink.w - 2 * trim, glyph.get_height())
            screen.blit(glyph, (x, y), area)
            x += area.w + LETTER_GAP

    def draw(self, screen: pygame.Surface, state: GameState, round_number: int,
             show_lives: bool = True) -> None:
        self._text(screen, TEXTS["hi_score"], RED, ROWS["hi_label"])
        self._text(screen, str(state.hi_score), WHITE, ROWS["hi_value"], "right")
        self._text(screen, TEXTS["player"], WHITE, ROWS["up_label"])
        self._text(screen, str(state.score), WHITE, ROWS["up_value"], "right")
        self._text_tight(screen, TEXTS["condition"], WHITE, ROWS["condition"])
        bar = pygame.Rect(self.panel.left, BAR_Y, self.panel.w, BAR_H)
        pygame.draw.rect(screen, CONDITION_COLORS[state.alert], bar)
        label = self.font.render(state.alert, False, BLACK)
        screen.blit(label, label.get_rect(center=bar.center))
        # Entre CONDITION y las vidas va el radar (lo dibuja s_minimap, según world.json).
        shown = min(state.lives, self.icons_max) if show_lives else 0  # sin partida no hay vidas
        for i in range(shown):  # alineadas a la izquierda, como en el original
            screen.blit(self.icon, (self.panel.left + i * ICON_SPACING, ICONS_Y))
        if show_lives and state.lives > self.icons_max:  # más vidas de las visibles: el total, abajo a la derecha
            total = self.font.render(str(state.lives), False, WHITE)
            spot = total.get_rect(bottomright=(self.panel.right, ICONS_Y + self.icon.get_height()))
            pygame.draw.rect(screen, BLACK, spot.inflate(2, 0))
            screen.blit(total, spot)
        self._text(screen, TEXTS["round"], WHITE, ROWS["round"])
        self._text(screen, str(round_number), WHITE, ROWS["round"], "right")

    def draw_cheat(self, screen: pygame.Surface, state: GameState) -> None:
        """Aviso del modo trampa, para que quede claro que la partida no es legítima."""
        if state.cheat:
            self._text(screen, TEXTS["cheat"], RED, ROWS["cheat"], "center")
