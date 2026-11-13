import pygame

from src.create.prefab_creator import create_image, create_stars, create_text
from src.ecs.systems.s_rendering import system_rendering
from src.ecs.systems.s_star import system_star_blink, system_star_fall, system_star_rendering
from src.engine.input.command import Phase
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator


class TitleScene(Scene):
    def do_create(self) -> None:
        w, h = self.engine.screen.get_size()
        self.area = self.engine.screen.get_rect()
        create_stars(self.world, self.engine.cfg_world, self.area)
        create_image(self.world, "title", pygame.Vector2(w / 2, h * 0.35))
        create_text(self.world, "PRESS START", pygame.Color(255, 255, 255),
                    pygame.Vector2(w / 2, h * 0.75))
        ServiceLocator.music.play("title")

    def do_action(self, action: str, phase: Phase) -> None:
        if action == "SELECT" and phase == Phase.START:
            self.engine.switch_scene("PLAY")

    def do_update(self, delta_time: float) -> None:
        system_star_blink(self.world, delta_time)
        system_star_fall(self.world, self.area, self.engine.cfg_world["stars_menu_speed"], delta_time)

    def do_draw(self, screen: pygame.Surface) -> None:
        system_star_rendering(self.world, screen)
        system_rendering(self.world, screen)
