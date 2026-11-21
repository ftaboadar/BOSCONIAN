"""Prueba de humo sin ventana: arranca el motor, simula input y cambia de escena."""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import pygame

from src.ecs.components.c_shutter import ShutterState
from src.engine.game_engine import GameEngine
from src.engine.scenes.play_scene import PlayScene
from src.engine.scenes.title_scene import TitleScene

engine = GameEngine()
assert engine.screen.get_size() == (256, 208), engine.screen.get_size()
engine.delta_time = 1 / 60

# El juego arranca como el original: pantalla inicial -> logo sobre el verde -> créditos -> título.
engine._apply_scene_change(engine.cfg_scenes["start_scene"])
seen = [type(engine._current_scene).__name__]
for _ in range(60 * 40):
    engine._frame()
    name = type(engine._current_scene).__name__
    if name != seen[-1]:
        seen.append(name)
    if name == "TitleScene" and not engine.shutter.state is not ShutterState.IDLE:
        break
assert seen == ["SplashScene", "LogoSlideScene", "BylineScene", "TitleScene"], seen
assert isinstance(engine._current_scene, TitleScene)

# En el título un botón abre el menú y Enter elige «JUGAR»: cinemática del nivel y luego el juego.
for _ in range(60):
    engine._frame()
pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
engine._frame()
assert engine._current_scene.mode == "menu"
pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
engine._process_events()
assert engine._next_scene == "CUTSCENE"  # la cinemática de «LEVEL n» precede al nivel
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
