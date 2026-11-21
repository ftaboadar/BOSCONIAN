"""Línea de tiempo de eventos animados (imágenes, sprites, textos, animaciones, sonidos).

La usan las escenas de historia (splash, logo, créditos, cinemática del nivel) y el título: cada
evento de story.json aparece en su momento y las entidades se mueven con los sistemas ECS."""

import esper

from src.create.prefab_story import create_story_actor
from src.ecs.systems.s_animation import system_animation
from src.ecs.systems.s_arrival import system_arrival
from src.ecs.systems.s_destroy import system_destroy
from src.ecs.systems.s_lifetime import system_lifetime
from src.ecs.systems.s_movement import system_movement
from src.engine.sfx import play_sound


class Timeline:
    def __init__(self, world: esper.World, events: list[dict], colors: dict,
                 fields: dict | None = None) -> None:
        self.world = world
        self.colors = colors
        self.fields = fields or {}
        self.pending = sorted(events, key=lambda e: e["at"])  # estable: respeta el orden dado
        self.elapsed = 0.0
        self.groups: dict[str, list[int]] = {}  # entidades por `group`, para quitarlas juntas

    def update(self, delta_time: float) -> None:
        """Hace aparecer lo que toca y avanza lo que ya está en pantalla."""
        self.elapsed += delta_time
        while self.pending and self.pending[0]["at"] <= self.elapsed:
            self._fire(self.pending.pop(0))
        system_lifetime(self.world, delta_time)
        system_movement(self.world, delta_time)
        system_arrival(self.world, delta_time)
        system_animation(self.world, delta_time)
        system_destroy(self.world)

    def _fire(self, event: dict) -> None:
        if event["type"] == "sound":
            play_sound(event["sound"])
            return
        ent = create_story_actor(self.world, event, self.colors, self.fields)
        if "group" in event:
            self.groups.setdefault(event["group"], []).append(ent)

    def remove_group(self, group: str) -> None:
        """Quita las entidades de un grupo (y los eventos de ese grupo que aún no aparecieron)."""
        for ent in self.groups.pop(group, []):
            if self.world.entity_exists(ent):
                self.world.delete_entity(ent, immediate=True)
        self.pending = [e for e in self.pending if e.get("group") != group]
