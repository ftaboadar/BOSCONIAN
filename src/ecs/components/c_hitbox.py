import pygame


class CHitBox:
    """Caja de colisión centrada en CTransform.pos (+ offset), independiente del sprite.

    layer: categoría de la entidad (por ejemplo "PLAYER", "ENEMY", "OBSTACLE").
    mask: capas contra las que esta entidad choca. Basta con que una de las
    dos entidades incluya a la otra en su máscara para que el par se revise.
    """

    def __init__(self, size: pygame.Vector2, offset: pygame.Vector2 | None = None,
                 layer: str = "", mask: tuple[str, ...] = ()) -> None:
        self.size = pygame.Vector2(size)
        self.offset = pygame.Vector2(offset) if offset is not None else pygame.Vector2(0, 0)
        self.layer = layer
        self.mask = frozenset(mask)
