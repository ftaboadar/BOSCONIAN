"""Actores de las escenas de historia (intro animado y cutscene): imágenes, sprites, cajas,
textos y animaciones descritos por eventos de story.json."""

import esper
import pygame

from src.create.prefab_creator import logo_surface, scaled_to_width
from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_arrival import CArrival
from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.engine.service_locator import ServiceLocator, color_from_cfg, rect_from_cfg


def _vec(point: dict) -> pygame.Vector2:
    return pygame.Vector2(point["x"], point["y"])


def _event_surface(event: dict, menu_colors: dict, fields: dict) -> pygame.Surface:
    """Superficie de un evento image, sprite, box o text (el tipo frames usa su primer cuadro)."""
    kind = event["type"]
    if kind == "image":
        if event["image"] == "title":  # el logo del juego, sin su mancha translúcida
            return logo_surface(event.get("width"))
        surf = ServiceLocator.images.get(event["image"])
        return scaled_to_width(surf, event["width"]) if "width" in event else surf
    if kind == "box":
        surf = pygame.Surface((event["size"]["w"], event["size"]["h"]))
        surf.fill(color_from_cfg(event["color"]))
        return surf
    if kind == "text":
        color = event["color"]
        color = menu_colors[color] if isinstance(color, str) else color
        return ServiceLocator.fonts.get("main").render(
            event["text"].format(**fields), False, color_from_cfg(color))
    sheet = ServiceLocator.images.get(event.get("image", "ships"))
    if kind == "frames":
        return sheet.subsurface(rect_from_cfg(event["rects"][0]))
    surf = sheet.subsurface(rect_from_cfg(event["rect"])).copy()  # sprite
    if "colorkey" in event:  # fondo transparente (por ejemplo, el magenta de las bases)
        pixels = pygame.PixelArray(surf)
        pixels.replace(color_from_cfg(event["colorkey"]), pygame.Color(0, 0, 0, 0))
        pixels.close()
    if event.get("scale", 1) != 1:
        surf = pygame.transform.scale(surf, (surf.get_width() * event["scale"],
                                             surf.get_height() * event["scale"]))
    if event.get("rotate"):
        surf = pygame.transform.rotate(surf, event["rotate"])
    return surf


def create_story_actor(world: esper.World, event: dict, menu_colors: dict,
                       fields: dict | None = None) -> int:
    """Crea la entidad de un evento de historia en su posición inicial.

    Con `to` y `seconds` viaja en línea recta y se detiene al llegar (CArrival); con `life`
    desaparece pasado ese tiempo; un evento `frames` es una animación que no se repite y se
    marca para destruirse al terminar. Se dibuja como interfaz (sin cámara).
    """
    surf = _event_surface(event, menu_colors, fields or {})
    start = _vec(event["from"]) if "to" in event else _vec(event["pos"])
    comps = [CTransform(start), CSurface(surf)]
    if "to" in event:
        target = _vec(event["to"])
        comps.append(CVelocity((target - start) / event["seconds"]))
        comps.append(CArrival(event["seconds"], target))
    if event["type"] == "frames":
        sheet = ServiceLocator.images.get(event["image"])
        comps.append(CAnimation(sheet, [rect_from_cfg(r) for r in event["rects"]], event["framerate"],
                                loop=False))
    if "life" in event:
        comps.append(CLifetime(event["life"]))
    return world.create_entity(*comps)
