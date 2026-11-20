import pygame


class CAnimation:
    """Animación cuadro a cuadro: recorre rectángulos dentro de un sprite sheet."""

    def __init__(self, sheet: pygame.Surface, frames: list[pygame.Rect],
                 framerate: float, loop: bool) -> None:
        self.sheet = sheet
        self.frames = frames
        self.frame_time = 1.0 / framerate
        self.loop = loop
        self.curr_frame = 0
        self.curr_time = 0.0
