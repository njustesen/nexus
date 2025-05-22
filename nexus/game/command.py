from nexus.network.message import NetworkMessage


class CommandType:
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    MOVE_LEFT = "move_left"
    MOVE_RIGHT = "move_right"
    SHOOT = "shoot"
    RELOAD = "reload"
    USE_ITEM = "use_item"
    DROP_ITEM = "drop_item"
    PICK_UP_ITEM = "pick_up_item"
    MAKE_MOVE = "make_move"


class Command(NetworkMessage):

    def __init__(self, command_type: CommandType, data: dict) -> None:
        self.command_type = command_type
        self.data = data
