from game_update import GameUpdate


class GameState:

    def __init__(self) -> None:
        self.phase = GamePhase.LOBBY
        self.board = [['' for _ in range(3)] for _ in range(3)]  # Initialize empty board

    def update(self, update: GameUpdate):
        raise NotImplementedError("Subclasses must implement this method")


class GamePhase:
    LOBBY = "lobby"
    IN_GAME = "in_game"
    END_GAME = "end_game"
