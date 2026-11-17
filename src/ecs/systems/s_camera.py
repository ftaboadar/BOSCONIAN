import esper

from src.ecs.components.c_camera_target import CCameraTarget
from src.ecs.components.c_transform import CTransform
from src.engine.camera import Camera


def system_camera_follow(world: esper.World, camera: Camera) -> None:
    for _, (c_t, _c_c) in world.get_components(CTransform, CCameraTarget):
        camera.follow(c_t.pos)
        return
