"""HUD fijo: se dibuja en pantalla, sin pasar por la cámara. Lee todo del GameState."""

import pygame

from src.ecs.components.c_alert import AlertLevel
from src.engine.game_state import GameState

WHITE = pygame.Color(255, 255, 255)
YELLOW = pygame.Color(255, 220, 0)
RED = pygame.Color(255, 60, 60)
GREEN = pygame.Color(0, 255, 0)
PANEL_CX = 216  # centro del panel derecho (x 176-256)
ALERTS = {AlertLevel.GREEN: ("VERDE", GREEN), AlertLevel.YELLOW: ("AMARILLA", YELLOW),
          AlertLevel.RED: ("ROJA", RED)}


class Hud:
    def __init__(self, font: pygame.font.Font, icons_max: int) -> None:
        self.font = font
        self.icons_max = icons_max
        self.icon = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.polygon(self.icon, WHITE, [(4, 0), (8, 8), (0, 8)])

    def _text(self, screen: pygame.Surface, text: str, color: pygame.Color, center) -> None:
        surf = self.font.render(text, False, color)
        screen.blit(surf, surf.get_rect(center=center))

    def draw(self, screen: pygame.Surface, state: GameState, round_number: int) -> None:
        self._text(screen, "HI-SCORE", YELLOW, (PANEL_CX, 8))
        self._text(screen, str(state.hi_score), WHITE, (PANEL_CX, 18))
        self._text(screen, "1UP", YELLOW, (PANEL_CX, 34))
        self._text(screen, str(state.score), WHITE, (PANEL_CX, 44))
        shown = min(state.lives, self.icons_max)
        left = PANEL_CX - shown * 10 // 2
        for i in range(shown):
            screen.blit(self.icon, (left + i * 10, 140))
        if state.lives > self.icons_max:  # más vidas de las visibles: número total abajo a la derecha
            self._text(screen, str(state.lives), WHITE, (246, 202))
        self._text(screen, f"ROUND {round_number}", WHITE, (PANEL_CX, 190))

    def draw_alert(self, screen: pygame.Surface, level: AlertLevel) -> None:
        """Condición de alerta del nivel, escrita en su color."""
        name, color = ALERTS[level]
        self._text(screen, "ALERTA", WHITE, (PANEL_CX, 157))
        self._text(screen, name, color, (PANEL_CX, 167))

    def draw_cheat(self, screen: pygame.Surface, state: GameState) -> None:
        """Aviso del modo trampa, para que quede claro que la partida no es legítima."""
        if state.cheat:
            self._text(screen, "CHEAT", RED, (PANEL_CX, 178))
