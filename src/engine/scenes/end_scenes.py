"""Escenas de fin de partida. Mínimas: #31 (victoria) y #32 (derrota con continuar) las amplían."""

from src.engine.scenes.info_scene import InfoScene


class _EndScene(InfoScene):
    HINT = "ENTER: TITULO"

    def page(self) -> dict:
        base = self.engine.cfg_menu[self.CFG_KEY]
        s = self.engine.state
        extra = ["", f"PUNTAJE {s.score}", f"VIDAS {s.lives}", f"CONTINUACIONES {s.continues_used}"]
        return {"title": base["title"], "lines": base["lines"] + extra}


class VictoryScene(_EndScene):
    CFG_KEY = "victory"


class DefeatScene(_EndScene):
    CFG_KEY = "defeat"
