import pygame


class CAngleSprites:
    """Un sprite por cada paso de giro, en sentido horario empezando por arriba.

    Con 16 pasos hay uno cada 22,5 grados: el índice 0 mira hacia arriba, el 4 a la derecha,
    el 8 hacia abajo y el 12 a la izquierda."""

    def __init__(self, surfaces: list[pygame.Surface]) -> None:
        self.surfaces = surfaces
