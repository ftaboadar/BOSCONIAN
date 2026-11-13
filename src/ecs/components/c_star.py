import pygame


class CStar:
    """Estrella de fondo: posición en pantalla, color y parpadeo (alfa 0-255)."""

    def __init__(self, color: pygame.Color, blink_speed: float, phase: float) -> None:
        self.surf = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.surf.fill(color)
        self.blink_speed = blink_speed  # ciclos por segundo
        self.phase = phase  # 0..1, desfase distinto para cada estrella
