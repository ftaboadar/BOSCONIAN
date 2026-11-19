"""Estado de partida compartido entre escenas: vidas, puntaje, récord, nivel y continuaciones."""

from src.engine.data_loader import load_entity_cfg

REQUIRED = ("lives", "hi_score", "extra_life_first", "extra_life_step", "life_icons_max",
            "continue_seconds")


class GameState:
    def __init__(self, cfg: dict | None = None) -> None:
        self.cfg = cfg or load_entity_cfg("game", REQUIRED)
        self.hi_score = self.cfg["hi_score"]
        self.reset()

    def reset(self, level: int = 1) -> None:
        """Nueva partida. El récord se conserva mientras corre el programa."""
        self.level = level
        self.lives = self.cfg["lives"]
        self.score = 0
        self.continues_used = 0
        self.next_extra_life = self.cfg["extra_life_first"]
        self.cheat = False  # modo trampa (F1): invulnerable; se apaga al empezar partida nueva

    @property
    def game_over(self) -> bool:
        return self.lives <= 0

    def add_score(self, points: int) -> None:
        """Suma puntos, actualiza el HI-SCORE y concede vidas extra al cruzar cada umbral."""
        self.score += points
        self.hi_score = max(self.hi_score, self.score)
        while self.score >= self.next_extra_life:
            self.lives += 1
            self.next_extra_life += self.cfg["extra_life_step"]

    def lose_life(self) -> int:
        self.lives = max(0, self.lives - 1)
        return self.lives

    def continue_game(self) -> None:
        """Continuar tras la derrota: recupera las vidas y pierde el puntaje."""
        self.continues_used += 1
        self.lives = self.cfg["lives"]
        self.score = 0
        self.next_extra_life = self.cfg["extra_life_first"]
