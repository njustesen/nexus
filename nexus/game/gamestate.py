from enum import Enum
from typing import Any, Dict, Tuple, List, ClassVar, Optional
from dataclasses import dataclass, field
from nexus.network.update import Update
from nexus.network.command import Command
from nexus.network.player import NexusPlayer
from nexus.network.serializable import Serializable


class GamePhase(str, Enum):
    LOBBY = "lobby"
    IN_GAME = "in_game"
    END_GAME = "end_game"


@dataclass
class GameState(Serializable):
    """Base class for game states"""
    players: List[NexusPlayer] = field(default_factory=list)
    game_over: bool = False
    winner: Optional[str] = None
    phase: GamePhase = GamePhase.IN_GAME

    def get_player_perspective(self, player_index: int) -> Dict[str, Any]:
        """Get the game state from a specific player's perspective"""
        return {
            "game_over": self.game_over,
            "winner": self.winner,
            "phase": self.phase
        }

    def is_valid(self, cmd: Command, player_index: int) -> Tuple[bool, str]:
        """Validate if a command is valid for the current game state"""
        raise NotImplementedError("Subclasses must implement this method")

    def apply(self, update: Update) -> None:
        """Apply an update to the game state"""
        raise NotImplementedError("Subclasses must implement this method")
