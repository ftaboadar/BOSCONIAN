import pygame

from src.create.prefab_creator import create_image, create_text
from src.ecs.systems.s_rendering import system_rendering
from src.engine.input.command import Phase
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator


class TitleScene(Scene):
    def do_create(self) -> None:
        w, h = self.engine.screen.get_size()
        logo = ServiceLocator.images.get("title")
        create_image(self.world, "title",
                     pygame.Vector2((w - logo.get_width()) / 2, h * 0.25))
        prompt = ServiceLocator.fonts.get("main").size("PRESS START")[0]
        create_text(self.world, "PRESS START", pygame.Color(255, 255, 255),
                    pygame.Vector2((w - prompt) / 2, h * 0.75))
        ServiceLocator.music.play("title")

    def do_action(self, action: str, phase: Phase) -> None:
        if action == "SELECT" and phase == Phase.START:
            self.engine.switch_scene("PLAY")

    def do_draw(self, screen: pygame.Surface) -> None:
        system_rendering(self.world, screen)
