"""Estado de partida compartido entre escenas: vidas, puntaje, récord, nivel y continuaciones."""

from src.engine.data_loader import load_entity_cfg

ALERTS = ("GREEN", "YELLOW", "RED")  # indicador CONDITION; el sistema de alertas (#26) lo cambia

REQUIRED = ("lives", "hi_score", "extra_life_first", "extra_life_step", "life_icons_max",
            "continue_seconds")


class BlankState:
    """Lo que muestra la barra antes de cargar nada: todo en ceros (la pantalla inicial del original)."""

    hi_score = 0
    score = 0
    lives = 0
    alert = ALERTS[0]
    cheat = False


class GameState:
    def __init__(self, cfg: dict | None = None) -> None:
        self.cfg = cfg or load_entity_cfg("game", REQUIRED)
        self.hi_score = self.cfg["hi_score"]
        self.record_to_beat = self.hi_score
        self.reset()

    def reset(self, level: int = 1) -> None:
        """Nueva partida. El récord se conserva mientras corre el programa."""
        self.level = level
        self.lives = self.cfg["lives"]
        self.score = 0
        self.continues_used = 0
        self.game_over = False
        self.next_extra_life = self.cfg["extra_life_first"]
        self.record_to_beat = self.hi_score  # el récord con el que empieza esta partida (#43)
        self.alert = ALERTS[0]  # todo nivel empieza en verde
        self.cheat = False  # modo trampa (F1): invulnerable; se apaga al empezar partida nueva
        self.clear_level_progress()

    def clear_level_progress(self) -> None:
        """Olvida lo avanzado en el nivel en curso. Ese progreso sobrevive a perder una vida:
        las bases destruidas no vuelven y el tiempo hacia la alerta ROJA no se reinicia."""
        self.bases_destroyed: set[int] = set()  # índices en level["bases"]
        self.level_seconds = 0.0  # segundos de nivel jugado (CAlert.elapsed)

    @property
    def broke_record(self) -> bool:
        """True si en esta partida se superó el HI-SCORE con el que empezó (sigue siendo True
        tras continuar: el récord ya quedó subido)."""
        return self.hi_score > self.record_to_beat

    def add_score(self, points: int) -> None:
        """Suma puntos, actualiza el HI-SCORE y concede vidas extra al cruzar cada umbral:
        `extra_life_first` y después cada múltiplo de `extra_life_step`."""
        self.score += points
        self.hi_score = max(self.hi_score, self.score)
        step = self.cfg["extra_life_step"]
        while self.score >= self.next_extra_life:
            self.lives += 1
            # Tras la primera (50.000) siguen los múltiplos del paso: 100.000, 200.000...
            self.next_extra_life = (self.next_extra_life // step + 1) * step

    def lose_life(self) -> int:
        """Descuenta una vida. Con el contador en 0 aún queda la última nave: solo se acaba
        la partida al morir estando en 0 (4 vidas + la del cero = 5 intentos)."""
        if self.lives == 0:
            self.game_over = True
        else:
            self.lives -= 1
        return self.lives

    def continue_game(self) -> None:
        """Continuar tras la derrota: recupera las vidas y pierde el puntaje."""
        self.continues_used += 1
        self.game_over = False
        self.lives = self.cfg["lives"]
        self.score = 0
        self.next_extra_life = self.cfg["extra_life_first"]
        self.clear_level_progress()  # sin puntaje, el nivel también empieza de cero
