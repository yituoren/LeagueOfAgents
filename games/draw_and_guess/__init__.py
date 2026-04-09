from .engine import DrawAndGuessEngine
from .referee import DrawAndGuessReferee

# Generic entrypoints for config-driven dynamic loading
GameEngine = DrawAndGuessEngine
Referee = DrawAndGuessReferee

__all__ = ["DrawAndGuessEngine", "DrawAndGuessReferee", "GameEngine", "Referee"]
