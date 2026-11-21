from enum import Enum, auto


class EnemyState(Enum):
    CHASE = auto()     # persigue al jugador (seek), desviado según la dificultad
    LEAVE = auto()     # se aleja del jugador (flee)
    WANDER = auto()    # deambula al azar (wander)
    STRAIGHT = auto()  # va derecho sin desviarse


class CEnemyState:
    """Patrón State: estado actual de la IA de un enemigo y tiempo que lleva en él."""

    def __init__(self, kind: str, state: EnemyState, chase_seconds: float = 0.0,
                 after_chase: EnemyState | None = None) -> None:
        self.kind = kind  # I, P o E
        self.state = state
        self.time_in_state = 0.0
        self.chase_seconds = chase_seconds  # cuánto persigue antes de cambiar de estado
        self.after_chase = after_chase  # estado al que pasa entonces (None: sigue persiguiendo)
