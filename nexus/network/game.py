from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from nexus.game.gamestate import GamePhase, GameState
from nexus.network.player import NexusPlayer
from nexus.network.serializable import Serializable


@dataclass
class NexusGame(Serializable):
    """Represents a game instance in the Nexus framework"""
    name: str
    max_players: int
    phase: GamePhase
    password: Optional[str] = None
    players: List[NexusPlayer] = field(default_factory=list)
    game_state: Optional[GameState] = None
    is_matchmaking: bool = False
    data: Dict[str, Any] = field(default_factory=dict)