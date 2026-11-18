import pygame


class CBase:
    """Base enemiga. `orientation` (horizontal o vertical) es la dirección en la que
    el núcleo es vulnerable. Sus torretas y su núcleo son entidades con CBasePart."""

    def __init__(self, orientation: str, turret_wreck: pygame.Surface, turret_radius: int) -> None:
        self.orientation = orientation
        self.turret_wreck = turret_wreck    # sprite que queda donde se destruye una torreta
        self.turret_radius = turret_radius  # radio en px del hueco que deja la torreta
