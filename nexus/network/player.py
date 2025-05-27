from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from nexus.network.serializable import Serializable
import time

@dataclass
class NexusPlayer(Serializable):
    """Represents a player in the Nexus framework"""
    id: str
    name: str = ""
    game_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    connected: bool = True
    last_seen: float = field(default_factory=time.time)