import esper
import pygame

from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform


def system_rendering(world: esper.World, screen: pygame.Surface) -> None:
    for _, (c_t, c_s) in world.get_components(CTransform, CSurface):
        screen.blit(c_s.surf, c_t.pos)
