import pygame


class CHud:
    """Barra lateral (HI-SCORE, 1UP, CONDITION, vidas y ROUND): lo que hace falta para dibujarla.

    Textos, colores y posiciones salen de assets/cfg/hud.json; los valores que muestra, del
    GameState en cada frame (s_hud.py)."""

    def __init__(self, font: pygame.font.Font, icon: pygame.Surface, icons_max: int,
                 panel: pygame.Rect, texts: dict[str, str], colors: dict[str, pygame.Color],
                 condition_colors: dict[str, pygame.Color], rows: dict[str, int],
                 condition_bar: pygame.Rect, icons_y: int, icon_spacing: int,
                 letter_gap: int, trimmed_letters: dict[str, int]) -> None:
        self.font = font
        self.icon = icon              # la nave del jugador, mirando hacia arriba
        self.icons_max = icons_max    # mini-naves que caben; con más vidas se muestra el número
        self.panel = panel            # la barra: a la derecha del campo de juego
        self.texts = texts
        self.colors = colors          # text, highlight y bar_text
        self.condition_colors = condition_colors  # color de la barra de CONDITION por alerta
        self.rows = rows              # altura de cada renglón
        self.condition_bar = condition_bar
        self.icons_y = icons_y        # justo bajo el radar
        self.icon_spacing = icon_spacing
        self.letter_gap = letter_gap  # px entre letras de CONDITION, para que quepa en la barra
        self.trimmed_letters = trimmed_letters  # letra -> columnas que pierde por cada lado
