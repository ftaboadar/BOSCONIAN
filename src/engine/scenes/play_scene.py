import pygame

from src.create.prefab_creator import create_text
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_rendering import system_rendering
from src.engine.input.command import Phase
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator


class PlayScene(Scene):
    """Escena de nivel (marcador de posición del hito 5)."""

    def do_create(self) -> None:
        ServiceLocator.music.stop()
        create_text(self.world, "ROUND 1", pygame.Color(255, 255, 255),
                    pygame.Vector2(8, 8))

    def do_action(self, action: str, phase: Phase) -> None:
        if action == "PAUSE" and phase == Phase.START:
            self.engine.switch_scene("TITLE")

    def do_update(self, delta_time: float) -> None:
        system_movement(self.world, delta_time)

    def do_draw(self, screen: pygame.Surface) -> None:
        system_rendering(self.world, screen)
