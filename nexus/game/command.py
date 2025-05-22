from nexus.network.message import NetworkMessage


class CommandType:
    MAKE_MOVE = "make_move"
    SURRENDER = "surrender"

class Command(NetworkMessage):

    def __init__(self, command_type: CommandType, data: dict) -> None:
        self.command_type = command_type
        self.data = data
