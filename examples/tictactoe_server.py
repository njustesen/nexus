import asyncio
from typing import List, Dict, Any
from nexus.network.server import GameServer, Game, Player
from nexus.game.gamestate import GameState, GamePhase
from nexus.game.command import Command, CommandType


class TicTacToeGameState(GameState):
    def __init__(self):
        super().__init__()
        self.board: List[List[str]] = [['' for _ in range(3)] for _ in range(3)]
        self.current_player: str = 'X'  # X always goes first

    def to_dict(self) -> Dict[str, Any]:
        """Convert the game state to a dictionary"""
        base_state = super().to_dict()
        base_state.update({
            "board": self.board,
            "current_player": self.current_player
        })
        return base_state

    def get_player_perspective(self, player_index: int) -> Dict[str, Any]:
        """Get the game state from a specific player's perspective"""
        state = self.to_dict()
        player_symbol = "X" if player_index == 0 else "O"
        state["your_symbol"] = player_symbol
        state["is_your_turn"] = (self.current_player == player_symbol)
        return state

    def update(self, data: Dict[str, Any]) -> None:
        """Update the game state with new data"""
        super().update(data)
        if "board" in data:
            self.board = data["board"]
        if "current_player" in data:
            self.current_player = data["current_player"]


class TicTacToeServer(GameServer):
    def create_initial_game_state(self) -> GameState:
        return TicTacToeGameState()

    def get_player_game_state(self, game: Game, player: Player) -> dict:
        """Get the game state from a specific player's perspective"""
        player_index = game.players.index(player)
        return game.game_state.get_player_perspective(player_index)

    async def handle_game_command(self, game: Game, player: Player, cmd: Command):
        """Handle game-specific commands"""
        # Type cast to access TicTacToeGameState specific attributes
        game_state: TicTacToeGameState = game.game_state
        
        # Verify it's the player's turn
        player_symbol = 'X' if player == game.players[0] else 'O'
        if player_symbol != game_state.current_player:
            print(f"[Server] Not player's turn: {player.name}")
            return

        row, col = cmd.data["row"], cmd.data["col"]
        
        # Validate move
        if not (0 <= row < 3 and 0 <= col < 3) or game_state.board[row][col]:
            print(f"[Server] Invalid move: {row}, {col}")
            return
        
        # Make move
        game_state.board[row][col] = player_symbol
        print(f"[Server] Move made: {player_symbol} at {row}, {col}")
        
        # Check for win
        winner = self.check_winner(game_state.board)
        is_draw = all(all(cell != '' for cell in row) for row in game_state.board)
        
        # Update current player
        game_state.current_player = 'O' if player_symbol == 'X' else 'X'
        
        # Prepare update data
        update_data = game_state.to_dict()
        
        if winner:
            game_state.phase = GamePhase.END_GAME
            update_data["winner"] = winner
            print(f"[Server] Game ended: {winner} wins!")
        elif is_draw:
            game_state.phase = GamePhase.END_GAME
            update_data["winner"] = None
            print(f"[Server] Game ended: Draw!")
        
        # Send update to all players
        await self.send_game_update(game, "game_state_update", update_data)

    def check_winner(self, board: List[List[str]]) -> str | None:
        """Check if there's a winner on the board"""
        # Check rows and columns
        for i in range(3):
            if board[i][0] == board[i][1] == board[i][2] != '':
                return board[i][0]
            if board[0][i] == board[1][i] == board[2][i] != '':
                return board[0][i]
        
        # Check diagonals
        if board[0][0] == board[1][1] == board[2][2] != '':
            return board[0][0]
        if board[0][2] == board[1][1] == board[2][0] != '':
            return board[0][2]
        
        return None


if __name__ == "__main__":
    server = TicTacToeServer()
    asyncio.run(server.start()) 