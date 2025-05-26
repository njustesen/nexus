import asyncio
import pygame
import argparse
from typing import List, Tuple, Dict, Any, Optional
from nexus.network.server import NexusServer
from nexus.network.client import NexusClient
from nexus.game.game import NexusGame
from nexus.network.player import NexusPlayer
from nexus.game.gamestate import GameState, GamePhase
from nexus.network.update import Update, UpdateType
from nexus.network.command import Command, CommandType
from dataclasses import dataclass, field


@dataclass
class TicTacToeState(GameState):
    """Game state for Tic-tac-toe that works for both client and server"""
    board: List[List[str]] = field(default_factory=lambda: [['' for _ in range(3)] for _ in range(3)])
    current_player: str = 'X'  # X always goes first
    my_symbol: Optional[str] = None  # Used by client to track their symbol

    def get_player_perspective(self, player_index: int) -> Dict[str, Any]:
        """Get the game state from a specific player's perspective"""
        state = super().get_player_perspective(player_index)
        player_symbol = "X" if player_index == 0 else "O"
        state.update({
            "board": self.board,
            "current_player": self.current_player,
            "winner": self.winner,
            "my_symbol": player_symbol,
            "is_your_turn": (self.current_player == player_symbol)
        })
        return state

    def is_valid(self, cmd: Command, player_index: int) -> Tuple[bool, str]:
        """Validate if a move is valid"""
        # Get player's symbol
        player_symbol = "X" if player_index == 0 else "O"
        
        # Verify it's the player's turn
        if player_symbol != self.current_player:
            return False, f"Not your turn - it's {self.current_player}'s turn"

        # Validate move coordinates
        try:
            row, col = cmd.data["row"], cmd.data["col"]
        except KeyError:
            return False, "Invalid command: missing row or col"

        # Check if move is in bounds and cell is empty
        if not (0 <= row < 3 and 0 <= col < 3):
            return False, f"Invalid move: position ({row}, {col}) is out of bounds"
        if self.board[row][col]:
            return False, f"Invalid move: position ({row}, {col}) is already occupied"

        return True, ""

    def apply(self, update: Update) -> None:
        """Apply an update to the game state"""
        if update.update_type == UpdateType.GAME_STATE_UPDATE:
            if "row" in update.data and "col" in update.data:
                # First apply the move
                row, col = update.data["row"], update.data["col"]
                symbol = update.data["symbol"]
                print(f"[TicTacToeState] Applying move: row={row}, col={col}, symbol={symbol}")
                print(f"[TicTacToeState] Board before: {self.board}")
                self.board[row][col] = symbol
                print(f"[TicTacToeState] Board after: {self.board}")
                
                # Then check for win/draw
                if self.check_winner():
                    self.winner = symbol  # Use the symbol that just moved
                    self.game_over = True
                    self.phase = GamePhase.END_GAME
                    self.current_player = None
                elif self.is_draw():
                    self.game_over = True
                    self.winner = None
                    self.phase = GamePhase.END_GAME
                    self.current_player = None
                else:
                    # Only switch current player if game continues
                    self.current_player = 'O' if symbol == 'X' else 'X'

    def check_winner(self) -> str | None:
        """Check if there's a winner on the board"""
        # Check rows and columns
        for i in range(3):
            if self.board[i][0] == self.board[i][1] == self.board[i][2] != '':
                return self.board[i][0]
            if self.board[0][i] == self.board[1][i] == self.board[2][i] != '':
                return self.board[0][i]
        
        # Check diagonals
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != '':
            return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != '':
            return self.board[0][2]
        
        return None

    def is_draw(self) -> bool:
        """Check if the game is a draw"""
        return all(all(cell != '' for cell in row) for row in self.board)

    def is_valid_move(self, row: int, col: int) -> bool:
        """Check if a move is valid at the given position"""
        return 0 <= row < 3 and 0 <= col < 3 and self.board[row][col] == ''


class TicTacToeServer(NexusServer):
    def create_initial_game_state(self, players: List[NexusPlayer]) -> TicTacToeState:
        """Create the initial game state for a new game"""
        return TicTacToeState(players)


class TicTacToeGame(NexusGame[TicTacToeState]):
    def __init__(self, client: NexusClient):
        print("[Client] Initializing TicTacToe game")
        super().__init__(
            client=client,
            game_state=None,
            fps=30,
            width=600,
            height=600,
            title="Tic Tac Toe"
        )
        # Font
        self.font = pygame.font.Font(None, 36)

        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GRAY = (128, 128, 128)
        
        # Board dimensions
        self.CELL_SIZE = 150
        self.GRID_SIZE = 3
        self.BOARD_SIZE = self.CELL_SIZE * self.GRID_SIZE
        
        # Center the board
        self.board_x = (self.screen.get_width() - self.BOARD_SIZE) // 2
        self.board_y = (self.screen.get_height() - self.BOARD_SIZE) // 2
        print("[Client] Game window initialized")

    def update(self, events: List[pygame.event.EventType]):
        # Process our game-specific events
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                print("[Client] Mouse click detected")
                if self.game_state.phase == GamePhase.IN_GAME and \
                   self.game_state.my_symbol == self.game_state.current_player:
                    print("[Client] Processing mouse click - it's our turn")
                    self.handle_click(event.pos)
                else:
                    print(f"[Client] Ignoring click - phase: {self.game_state.phase}, " + \
                          f"my_symbol: {self.game_state.my_symbol}, " + \
                          f"current_player: {self.game_state.current_player}")
                    print(f"[Client] Game state: {self.game_state}")

    def handle_click(self, pos: Tuple[int, int]):
        # Convert screen coordinates to board coordinates
        x, y = pos
        row = (y - self.board_y) // self.CELL_SIZE
        col = (x - self.board_x) // self.CELL_SIZE
        
        print(f"[Client] Click at position ({x}, {y}) -> board coordinates ({row}, {col})")
        
        # Check if click is within board and cell is empty
        if 0 <= row < 3 and 0 <= col < 3:  # First check if within bounds
            if self.game_state.is_valid_move(row, col):
                print(f"[Client] Making move at ({row}, {col}) with symbol {self.game_state.my_symbol}")
                cmd = Command(CommandType.MAKE_MOVE, {
                    "row": row,
                    "col": col,
                    "symbol": self.game_state.my_symbol
                })
                self.send_command(cmd)
            else:
                print(f"[Client] Invalid move at ({row}, {col}): Cell already occupied")
        else:
            print(f"[Client] Invalid move at ({row}, {col}): Out of bounds")

    def draw(self):
        self.screen.fill(self.WHITE)
        
        # Draw the grid
        for i in range(4):
            # Vertical lines
            pygame.draw.line(
                self.screen, 
                self.BLACK,
                (self.board_x + i * self.CELL_SIZE, self.board_y),
                (self.board_x + i * self.CELL_SIZE, self.board_y + self.BOARD_SIZE),
                2
            )
            # Horizontal lines
            pygame.draw.line(
                self.screen,
                self.BLACK,
                (self.board_x, self.board_y + i * self.CELL_SIZE),
                (self.board_x + self.BOARD_SIZE, self.board_y + i * self.CELL_SIZE),
                2
            )
        
        if self.game_state is None:
            text = self.font.render("Waiting for opponent...", True, self.BLACK)
            text_rect = text.get_rect(center=(self.screen.get_width() // 2, 30))
            self.screen.blit(text, text_rect)
        else:
            # Draw X's and O's
            for row in range(3):
                for col in range(3):
                    cell = self.game_state.board[row][col]
                    if cell:
                        x = self.board_x + col * self.CELL_SIZE + self.CELL_SIZE // 2
                        y = self.board_y + row * self.CELL_SIZE + self.CELL_SIZE // 2
                        if cell == 'X':
                            self.draw_x(x, y)
                        else:
                            self.draw_o(x, y)
        
            # Draw game status
            status_text = ""
            if self.game_state.phase == GamePhase.IN_GAME:
                if self.game_state.my_symbol == self.game_state.current_player:
                    status_text = f"Your turn! (You are {self.game_state.my_symbol})"
                else:
                    status_text = f"Opponent's turn (You are {self.game_state.my_symbol})"
            elif self.game_state.phase == GamePhase.END_GAME:
                if self.game_state.winner:
                    if self.game_state.winner == self.game_state.my_symbol:
                        status_text = "You won!"
                    else:
                        status_text = "You lost!"
                else:
                    status_text = "It's a draw!"
        
            text = self.font.render(status_text, True, self.BLACK)
            text_rect = text.get_rect(center=(self.screen.get_width() // 2, 30))
            self.screen.blit(text, text_rect)
        
        pygame.display.flip()

    def draw_x(self, x: int, y: int):
        size = self.CELL_SIZE // 3
        pygame.draw.line(
            self.screen, self.BLACK,
            (x - size, y - size),
            (x + size, y + size),
            3
        )
        pygame.draw.line(
            self.screen, self.BLACK,
            (x - size, y + size),
            (x + size, y - size),
            3
        )

    def draw_o(self, x: int, y: int):
        size = self.CELL_SIZE // 3
        pygame.draw.circle(
            self.screen,
            self.BLACK,
            (x, y),
            size,
            3
        )


def run_server(args):
    """Run the game in server mode"""
    print(f"[Server] Starting server on port {args.port}")
    server = TicTacToeServer()
    asyncio.run(server.start())


def run_client(args):
    """Run the game in client mode"""
    print(f"[Client] Starting with args: {args}")
    
    # Create client and connect to server
    print(f"[Client] Connecting to server at {args.host}:{args.port}")
    client = NexusClient(args.host, args.port)
    client.connect()
    print("[Client] Connected to server")
    
    # Send initial command based on arguments
    if args.create:
        print(f"[Client] Creating game: {args.create}")
        cmd = Command(CommandType.CREATE_GAME, {
            "game_name": args.create,
            "password": args.password,
            "player_name": args.name
        })
    elif args.join:
        print(f"[Client] Joining game: {args.join}")
        cmd = Command(CommandType.JOIN_GAME, {
            "game_name": args.join,
            "password": args.password,
            "player_name": args.name
        })
    else:  # matchmaking
        print("[Client] Starting matchmaking")
        cmd = Command(CommandType.FIND_GAME, {
            "player_name": args.name
        })
    
    client.send(cmd)
    print("[Client] Initial command sent")
    
    # Start the game
    print("[Client] Starting game loop")
    game = TicTacToeGame(client)
    game.run()


def main():
    parser = argparse.ArgumentParser(description='TicTacToe Game')
    subparsers = parser.add_subparsers(dest='mode', help='Mode to run in', required=True)
    
    # Server mode
    server_parser = subparsers.add_parser('server', help='Run in server mode')
    server_parser.add_argument('--port', type=int, default=8765, help='Server port')
    
    # Client mode
    client_parser = subparsers.add_parser('client', help='Run in client mode')
    client_parser.add_argument('--host', default='localhost', help='Server host')
    client_parser.add_argument('--port', type=int, default=8765, help='Server port')
    client_parser.add_argument('--name', required=True, help='Your player name')
    group = client_parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--create', help='Create a new game with the given name')
    group.add_argument('--join', help='Join an existing game with the given name')
    group.add_argument('--matchmaking', action='store_true', help='Find a game via matchmaking')
    client_parser.add_argument('--password', help='Password for creating/joining a game')
    
    args = parser.parse_args()
    
    if args.mode == 'server':
        run_server(args)
    else:
        run_client(args)


if __name__ == "__main__":
    main() 