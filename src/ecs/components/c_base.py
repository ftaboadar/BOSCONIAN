import pygame


class CBase:
    """Base enemiga. `orientation` (horizontal o vertical) es la dirección en la que
    el núcleo es vulnerable. Sus torretas y su núcleo son entidades con CBasePart."""

    def __init__(self, orientation: str, turret_wreck: pygame.Surface, turret_radius: int,
                 core_frames: list[pygame.Surface], core_radius: int, index: int = 0) -> None:
        self.index = index                  # posición de la base en la lista del nivel
        self.orientation = orientation
        self.turret_wreck = turret_wreck    # sprite que queda donde se destruye una torreta
        self.turret_radius = turret_radius  # radio en px del hueco que deja la torreta
        self.core_frames = core_frames      # del núcleo cerrado al abierto
        self.core_radius = core_radius
