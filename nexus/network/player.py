from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from nexus.network.serializable import Serializable

@dataclass
class NexusPlayer(Serializable):
    """Represents a player in the Nexus framework"""
    id: str
    name: str = ""
    game_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)