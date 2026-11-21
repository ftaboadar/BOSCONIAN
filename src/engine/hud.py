"""HUD fijo: se dibuja en pantalla, sin pasar por la cámara. Lee todo del GameState.

Panel derecho, de arriba abajo: HI-SCORE, 1UP, el radar (lo dibuja s_minimap), CONDITION,
las vidas como mini-naves y la ronda."""

import pygame

from src.engine.game_state import GameState

WHITE = pygame.Color(255, 255, 255)
YELLOW = pygame.Color(255, 220, 0)
RED = pygame.Color(255, 60, 60)
GREEN = pygame.Color(60, 255, 60)
CONDITION_COLORS = {"GREEN": GREEN, "YELLOW": YELLOW, "RED": RED}
PANEL_CX = 216  # centro del panel derecho (x 176-256)
ICON_SPACING = 16  # separación entre mini-naves (el sprite mide 15 px de ancho)
ICONS_Y = 165
ROUND_Y = 192


class Hud:
    def __init__(self, font: pygame.font.Font, icons_max: int, icon: pygame.Surface) -> None:
        self.font = font
        self.icons_max = icons_max
        self.icon = icon  # la nave del jugador, mirando hacia arriba

    def _text(self, screen: pygame.Surface, text: str, color: pygame.Color, center) -> None:
        surf = self.font.render(text, False, color)
        screen.blit(surf, surf.get_rect(center=center))

    def draw(self, screen: pygame.Surface, state: GameState, round_number: int) -> None:
        self._text(screen, "HI-SCORE", YELLOW, (PANEL_CX, 8))
        self._text(screen, str(state.hi_score), WHITE, (PANEL_CX, 18))
        self._text(screen, "1UP", YELLOW, (PANEL_CX, 34))
        self._text(screen, str(state.score), WHITE, (PANEL_CX, 44))
        # El radar ocupa de y=54 a y=134 (lo dibuja s_minimap).
        self._text(screen, "CONDITION", WHITE, (PANEL_CX, 141))
        self._text(screen, state.alert, CONDITION_COLORS[state.alert], (PANEL_CX, 150))
        shown = min(state.lives, self.icons_max)
        left = PANEL_CX - shown * ICON_SPACING // 2
        for i in range(shown):
            screen.blit(self.icon, (left + i * ICON_SPACING, ICONS_Y))
        if state.lives > self.icons_max:  # más vidas de las visibles: número total abajo a la derecha
            self._text(screen, str(state.lives), WHITE, (246, 202))
        self._text(screen, f"ROUND {round_number}", WHITE, (PANEL_CX, ROUND_Y))

    def draw_cheat(self, screen: pygame.Surface, state: GameState) -> None:
        """Aviso del modo trampa, para que quede claro que la partida no es legítima."""
        if state.cheat:
            self._text(screen, "CHEAT", RED, (PANEL_CX, 159))
