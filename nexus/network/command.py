from dataclasses import dataclass, field
from typing import Dict, Any
from enum import Enum
from nexus.network.serializable import Serializable


class CommandType(str, Enum):
    MAKE_MOVE = "make_move"
    SURRENDER = "surrender"
    CREATE_GAME = "create_game"
    JOIN_GAME = "join_game"
    FIND_GAME = "find_game"

@dataclass
class Command(Serializable):
    command_type: CommandType
    data: Dict[str, Any] = field(default_factory=dict)
