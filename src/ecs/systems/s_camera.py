import esper
import pygame

from src.ecs.components.c_camera_target import CCameraTarget
from src.ecs.components.c_transform import CTransform
from src.engine.camera import Camera


def system_camera_follow(world: esper.World, camera: Camera) -> None:
    for _, (c_t, _c_c) in world.get_components(CTransform, CCameraTarget):
        camera.follow(c_t.pos)
        return
    # Sin objetivo (por ejemplo, el jugador murió) la cámara queda quieta.
    camera.delta = pygame.Vector2()
