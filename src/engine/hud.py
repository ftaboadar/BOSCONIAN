"""HUD fijo: se dibuja en pantalla, sin pasar por la cámara. Lee todo del GameState.

La distribución sale de medir el Bosconian original (X68000): una barra de 64 px a la derecha
del campo de juego de 192 px. De arriba abajo: HI-SCORE (rojo) y su valor a la derecha, 1UP a
la izquierda y su valor a la derecha, CONDITION con una barra de color a todo el ancho, el radar
(lo dibuja s_minimap), las vidas como mini-naves y ROUND pegado al borde de abajo."""

import pygame

from src.engine.game_state import GameState

WHITE = pygame.Color(255, 255, 255)
RED = pygame.Color(255, 60, 40)
BLACK = pygame.Color(0, 0, 0)
# Color de la barra de CONDITION para cada alerta (texto negro encima).
CONDITION_COLORS = {"GREEN": pygame.Color(128, 255, 160), "YELLOW": pygame.Color(255, 225, 60),
                    "RED": pygame.Color(255, 80, 80)}
LETTER_ADVANCE = 7  # CONDITION tiene 9 letras y debe caber en 64 px: el original las aprieta
ROWS = {"hi_label": 0, "hi_value": 8, "up_label": 16, "up_value": 24, "cheat": 36,
        "condition": 48, "round": 200}
BAR_Y, BAR_H = 61, 15
ICONS_Y = 180
ICON_SPACING = 16  # 4 mini-naves llenan justo los 64 px de la barra


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

    def _tight(self, screen: pygame.Surface, text: str, color: pygame.Color, y: int) -> None:
        """Texto con las letras más juntas, para que quepa en el ancho de la barra."""
        for i, char in enumerate(text):
            screen.blit(self.font.render(char, False, color), (self.panel.left + i * LETTER_ADVANCE, y))

    def draw(self, screen: pygame.Surface, state: GameState, round_number: int) -> None:
        self._text(screen, "HI-SCORE", RED, ROWS["hi_label"])
        self._text(screen, str(state.hi_score), WHITE, ROWS["hi_value"], "right")
        self._text(screen, "1UP", WHITE, ROWS["up_label"])
        self._text(screen, str(state.score), WHITE, ROWS["up_value"], "right")
        self._tight(screen, "CONDITION", WHITE, ROWS["condition"])
        bar = pygame.Rect(self.panel.left, BAR_Y, self.panel.w, BAR_H)
        pygame.draw.rect(screen, CONDITION_COLORS[state.alert], bar)
        label = self.font.render(state.alert, False, BLACK)
        screen.blit(label, label.get_rect(center=bar.center))
        # El radar ocupa de y=80 a y=176 (lo dibuja s_minimap).
        shown = min(state.lives, self.icons_max)
        left = self.panel.centerx - shown * ICON_SPACING // 2
        for i in range(shown):
            screen.blit(self.icon, (left + i * ICON_SPACING, ICONS_Y))
        if state.lives > self.icons_max:  # más vidas de las visibles: el total, abajo a la derecha
            total = self.font.render(str(state.lives), False, WHITE)
            spot = total.get_rect(bottomright=(self.panel.right, ICONS_Y + self.icon.get_height()))
            pygame.draw.rect(screen, BLACK, spot.inflate(2, 0))
            screen.blit(total, spot)
        self._text(screen, "ROUND", WHITE, ROWS["round"])
        self._text(screen, str(round_number), WHITE, ROWS["round"], "right")

    def draw_cheat(self, screen: pygame.Surface, state: GameState) -> None:
        """Aviso del modo trampa, para que quede claro que la partida no es legítima."""
        if state.cheat:
            self._text(screen, "CHEAT", RED, ROWS["cheat"], "center")
