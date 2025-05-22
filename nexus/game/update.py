from nexus.network.message import NetworkMessage

class UpdateType:
    PLAYER_UPDATE = "player_update"
    ENTITY_UPDATE = "entity_update"
    ITEM_UPDATE = "item_update"
    PROJECTILE_UPDATE = "projectile_update"
    GAME_STATE_UPDATE = "game_state_update"


class Update(NetworkMessage):

    def __init__(self, update_type: UpdateType, data: dict) -> None:
        self.update_type = update_type
        self.data = data

