"""Patrón Escena: cada escena tiene su propio mundo ECS y ciclo de vida."""

import esper
import pygame

from src.ecs.systems.s_minimap import system_minimap_rendering
from src.engine.input.command import Phase


class Scene:
    # La barra lateral (HI-SCORE, 1UP, radar, CONDITION, vidas y ROUND) es parte fija de la
    # pantalla del juego: el motor la dibuja tras cada escena que la tenga. La escena solo
    # dibuja el campo de juego (engine.viewport); lo que se pase de ahí queda tapado.
    has_panel = True

    def __init__(self, engine) -> None:
        self.engine = engine
        self.world = esper.World()

    def do_create(self) -> None:
        """Crea entidades y arranca recursos de la escena."""

    def do_action(self, action: str, phase: Phase) -> None:
        """Recibe una acción lógica del input."""

    def do_any_key(self) -> None:
        """Se llama con cualquier tecla pulsada, esté o no mapeada a una acción."""

    def do_update(self, delta_time: float) -> None:
        """Ejecuta los sistemas de la escena."""

    def do_draw(self, screen: pygame.Surface) -> None:
        """Dibuja la escena."""

    def panel_round(self) -> int:
        """Número que muestra la barra en ROUND."""
        return self.engine.level

    def draw_radar(self, screen: pygame.Surface) -> None:
        """Radar de la barra lateral. Por defecto, vacío: solo el marco."""
        system_minimap_rendering(esper.World(), screen, self.engine.cfg_world["minimap"],
                                 self.engine.world_size)

    def do_clean(self) -> None:
        """Libera la escena."""
        self.world.clear_database()
