"""HUD fijo: se dibuja en pantalla, sin pasar por la cámara, con los valores del GameState.

La distribución sale de medir el Bosconian original (X68000): una barra de 64 px a la derecha
del campo de juego de 192 px. De arriba abajo: HI-SCORE (rojo) y su valor a la derecha, 1UP a
la izquierda y su valor a la derecha, CONDITION con una barra de color a todo el ancho, el radar
(lo dibuja s_minimap), las vidas como mini-naves y ROUND pegado al borde de abajo."""

import esper
import pygame

from src.ecs.components.c_hud import CHud


def _text(screen: pygame.Surface, c_hud: CHud, text: str, color: pygame.Color, y: int,
          align: str = "left") -> None:
    surf = c_hud.font.render(text, False, color)
    panel = c_hud.panel
    x = {"left": panel.left, "right": panel.right - surf.get_width(),
         "center": panel.centerx - surf.get_width() // 2}[align]
    screen.blit(surf, (x, y))


def _text_tight(screen: pygame.Surface, c_hud: CHud, text: str, color: pygame.Color, y: int) -> None:
    """Texto con las letras más juntas, para que quepa en el ancho de la barra: CONDITION tiene
    9 letras de 7 px y debe caber en 64 px. Cada letra se recorta a su tinta, se separa
    `letter_gap` px y pierde las columnas que diga `trimmed_letters` (los remates de la I)."""
    x = c_hud.panel.left
    for char in text:
        glyph = c_hud.font.render(char, False, color)
        ink = glyph.get_bounding_rect()
        trim = c_hud.trimmed_letters.get(char, 0)
        area = pygame.Rect(ink.left + trim, 0, ink.w - 2 * trim, glyph.get_height())
        screen.blit(glyph, (x, y), area)
        x += area.w + c_hud.letter_gap


def system_hud_rendering(world: esper.World, screen: pygame.Surface, state, round_number: int,
                         show_lives: bool = True) -> None:
    """Dibuja la barra con los valores de `state` (un GameState, o BlankState antes de cargar)."""
    for _, c_hud in world.get_component(CHud):
        texts, rows, panel = c_hud.texts, c_hud.rows, c_hud.panel
        white, red, black = (c_hud.colors[k] for k in ("text", "highlight", "bar_text"))
        _text(screen, c_hud, texts["hi_score"], red, rows["hi_label"])
        _text(screen, c_hud, str(state.hi_score), white, rows["hi_value"], "right")
        _text(screen, c_hud, texts["player"], white, rows["up_label"])
        _text(screen, c_hud, str(state.score), white, rows["up_value"], "right")
        _text_tight(screen, c_hud, texts["condition"], white, rows["condition"])
        bar = c_hud.condition_bar
        pygame.draw.rect(screen, c_hud.condition_colors[state.alert], bar)
        label = c_hud.font.render(state.alert, False, black)
        screen.blit(label, label.get_rect(center=bar.center))
        # Entre CONDITION y las vidas va el radar (lo dibuja s_minimap, según world.json).
        shown = min(state.lives, c_hud.icons_max) if show_lives else 0  # sin partida no hay vidas
        for i in range(shown):  # alineadas a la izquierda, como en el original
            screen.blit(c_hud.icon, (panel.left + i * c_hud.icon_spacing, c_hud.icons_y))
        if show_lives and state.lives > c_hud.icons_max:  # más vidas de las visibles: el total, abajo a la derecha
            total = c_hud.font.render(str(state.lives), False, white)
            spot = total.get_rect(
                bottomright=(panel.right, c_hud.icons_y + c_hud.icon.get_height()))
            pygame.draw.rect(screen, black, spot.inflate(2, 0))
            screen.blit(total, spot)
        _text(screen, c_hud, texts["round"], white, rows["round"])
        _text(screen, c_hud, str(round_number), white, rows["round"], "right")


def system_cheat_rendering(world: esper.World, screen: pygame.Surface, cheat: bool) -> None:
    """Aviso del modo trampa, para que quede claro que la partida no es legítima."""
    if not cheat:
        return
    for _, c_hud in world.get_component(CHud):
        _text(screen, c_hud, c_hud.texts["cheat"], c_hud.colors["highlight"], c_hud.rows["cheat"],
              "center")
