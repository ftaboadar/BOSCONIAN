import esper
import pygame

from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_world import CWorld
from src.engine.camera import Camera


def system_rendering(world: esper.World, screen: pygame.Surface) -> None:
    """Dibuja entidades de interfaz: `pos` es el centro y no depende de la cámara."""
    for ent, (c_t, c_s) in world.get_components(CTransform, CSurface):
        if world.has_component(ent, CWorld):
            continue
        screen.blit(c_s.surf, c_s.surf.get_rect(center=(round(c_t.pos.x), round(c_t.pos.y))))


def system_world_rendering(world: esper.World, screen: pygame.Surface, camera: Camera) -> None:
    """Dibuja entidades del mundo según la cámara, recortadas al viewport."""
    screen.set_clip(camera.viewport)
    for _, (c_t, c_s, _c_w) in world.get_components(CTransform, CSurface, CWorld):
        p = camera.world_to_screen(c_t.pos)
        screen.blit(c_s.surf, c_s.surf.get_rect(center=(round(p.x), round(p.y))))
    screen.set_clip(None)
