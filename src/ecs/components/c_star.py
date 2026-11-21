import pygame


class CStar:
    """Estrella de fondo: su punto de color y su parpadeo (alfa 0-255). La posición va en CTransform."""

    def __init__(self, surf: pygame.Surface, blink_speed: float, phase: float) -> None:
        self.surf = surf  # un píxel del color de la estrella, con canal alfa
        self.blink_speed = blink_speed  # ciclos por segundo
        self.phase = phase  # 0..1, desfase distinto para cada estrella
