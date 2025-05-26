from dataclasses import dataclass, field
from typing import Dict, Any
from enum import Enum
from nexus.network.serializable import Serializable


class UpdateType(str, Enum):
    GAME_CREATED = "game_created"
    GAME_OVER = "game_over"
    GAME_STARTED = "game_started"
    GAME_STATE_UPDATE = "game_state_update"
    ERROR = "error"

@dataclass
class Update(Serializable):
    update_type: UpdateType
    data: Dict[str, Any] = field(default_factory=dict)

