"""Flujo de niveles: decide a qué escena ir al superar un nivel o al morir el jugador."""

from src.engine.game_state import GameState


def after_level_cleared(state: GameState, levels: list[int]) -> str:
    """Pasa al siguiente nivel de `levels`; tras el último va a VICTORY."""
    later = [n for n in levels if n > state.level]
    if not later:
        return "VICTORY"
    state.level = later[0]
    return "PLAY"


def after_game_end(state: GameState) -> str:
    """Tras victoria o derrota definitiva: la felicitación si se superó el HI-SCORE, o el título."""
    return "RECORD" if state.broke_record else "TITLE"


def after_player_died(state: GameState) -> str:
    """Descuenta una vida: con vidas repite el nivel; sin vidas va a DEFEAT."""
    state.lose_life()
    return "DEFEAT" if state.game_over else "PLAY"
