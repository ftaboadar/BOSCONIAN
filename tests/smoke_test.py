"""Prueba de humo sin ventana: arranca el motor, simula input y cambia de escena."""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import pygame

from src.engine.game_engine import GameEngine
from src.engine.scenes.play_scene import PlayScene
from src.engine.scenes.title_scene import TitleScene

engine = GameEngine()
assert engine.screen.get_size() == (256, 208), engine.screen.get_size()
engine._apply_scene_change("TITLE")
assert isinstance(engine._current_scene, TitleScene)

for _ in range(5):
    engine._calculate_time()
    engine._process_events()
    engine._update()
    engine._draw()

pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
engine._process_events()
assert engine._next_scene == "CUTSCENE"  # la cutscene (#37) precede al nivel
engine._apply_scene_change(engine._next_scene)
pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
engine._current_scene.elapsed = 1.0  # pasada la gracia, una tecla la salta
engine._process_events()
assert engine._next_scene == "PLAY"
engine._apply_scene_change(engine._next_scene)
assert isinstance(engine._current_scene, PlayScene)
for _ in range(5):
    engine._update()
    engine._draw()

engine._clean()
print("SMOKE OK")
