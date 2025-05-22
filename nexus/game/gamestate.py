from enum import Enum
from typing import Any, Dict
from nexus.game.update import Update


class GamePhase(str, Enum):
    LOBBY = "lobby"
    IN_GAME = "in_game"
    END_GAME = "end_game"


class GameState:

    def __init__(self) -> None:
        self.phase: GamePhase = GamePhase.LOBBY
        self.board = [['' for _ in range(3)] for _ in range(3)]  # Initialize empty board

    def to_dict(self) -> Dict[str, Any]:
        """Convert the game state to a dictionary for serialization"""
        return {
            "phase": self.phase
        }

    def get_player_perspective(self, player_index: int) -> Dict[str, Any]:
        """
        Get the game state from a specific player's perspective.
        This base implementation just returns the basic state.
        Game-specific implementations should override this to add their own state.
        """
        return self.to_dict()

    def update(self, data: Dict[str, Any]) -> None:
        """
        Update the game state with new data.
        This base implementation only updates the phase.
        Game-specific implementations should override this to handle their own state.
        """
        if "phase" in data:
            self.phase = GamePhase(data["phase"])
