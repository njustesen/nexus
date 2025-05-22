import pygame
import sys
import json
import argparse
from typing import Optional, List, Tuple
from client import WebSocketClient
from game import NetworkGame
from game_state import GameState, GamePhase
from game_update import GameUpdate, UpdateType
from command import Command, CommandType

class TicTacToeState(GameState):
    def __init__(self):
        super().__init__()
        self.board = [['' for _ in range(3)] for _ in range(3)]
        self.current_player = 'X'
        self.winner = None
        self.my_symbol = None
        print("[Client] TicTacToe state initialized")

    def update(self, update: GameUpdate):
        print(f"[Client] Received game update: {update.data}")
        if update.update_type == UpdateType.GAME_STATE_UPDATE:
            if "board" in update.data:
                self.board = update.data["board"]
            if "current_player" in update.data:
                self.current_player = update.data["current_player"]
            if "winner" in update.data:
                self.winner = update.data["winner"]
            if "your_symbol" in update.data:
                self.my_symbol = update.data["your_symbol"]
                print(f"[Client] Assigned symbol: {self.my_symbol}")
            if "phase" in update.data:
                self.phase = update.data["phase"]
                print(f"[Client] Game phase updated to: {self.phase}")
            else:
                print(f"[Client] Warning: No phase in update data: {update.data}")

    def is_valid_move(self, row: int, col: int) -> bool:
        return 0 <= row < 3 and 0 <= col < 3 and self.board[row][col] == ''

class TicTacToe(NetworkGame):
    def __init__(self, client: WebSocketClient):
        print("[Client] Initializing TicTacToe game")
        super().__init__(
            client=client,
            game_state=TicTacToeState(),
            fps=30,
            width=600,
            height=600,
            title="Tic Tac Toe"
        )
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
        font = pygame.font.Font(None, 36)
        if self.game_state.phase == GamePhase.LOBBY:
            text = font.render("Waiting for opponent...", True, self.BLACK)
        elif self.game_state.phase == GamePhase.IN_GAME:
            if self.game_state.my_symbol == self.game_state.current_player:
                text = font.render("Your turn!", True, self.BLACK)
            else:
                text = font.render("Opponent's turn", True, self.BLACK)
        elif self.game_state.phase == GamePhase.END_GAME:
            if self.game_state.winner:
                if self.game_state.winner == self.game_state.my_symbol:
                    text = font.render("You won!", True, self.BLACK)
                else:
                    text = font.render("You lost!", True, self.BLACK)
            else:
                text = font.render("It's a draw!", True, self.BLACK)
        
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

def main():
    parser = argparse.ArgumentParser(description='TicTacToe Game Client')
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', type=int, default=8765, help='Server port')
    parser.add_argument('--name', required=True, help='Your player name')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--create', help='Create a new game with the given name')
    group.add_argument('--join', help='Join an existing game with the given name')
    group.add_argument('--matchmaking', action='store_true', help='Find a game via matchmaking')
    parser.add_argument('--password', help='Password for creating/joining a game')
    
    args = parser.parse_args()
    print(f"[Client] Starting with args: {args}")
    
    # Create client and connect to server
    print(f"[Client] Connecting to server at {args.host}:{args.port}")
    client = WebSocketClient(args.host, args.port)
    client.connect()
    print("[Client] Connected to server")
    
    # Send initial command based on arguments
    if args.create:
        print(f"[Client] Creating game: {args.create}")
        cmd = Command("create_game", {
            "name": args.create,
            "password": args.password,
            "player_name": args.name
        })
    elif args.join:
        print(f"[Client] Joining game: {args.join}")
        cmd = Command("join_game", {
            "name": args.join,
            "password": args.password,
            "player_name": args.name
        })
    else:  # matchmaking
        print("[Client] Starting matchmaking")
        cmd = Command("find_game", {
            "player_name": args.name
        })
    
    client.send(cmd)
    print("[Client] Initial command sent")
    
    # Start the game
    print("[Client] Starting game loop")
    game = TicTacToe(client)
    game.run()

if __name__ == "__main__":
    main() 