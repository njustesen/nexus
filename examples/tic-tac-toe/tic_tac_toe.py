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
from enum import Enum
import pygame.freetype

# Initialize Pygame
pygame.init()
pygame.freetype.init()

# Constants
WINDOW_SIZE = (800, 600)
CELL_SIZE = 100
GRID_SIZE = 3
GRID_WIDTH = CELL_SIZE * GRID_SIZE
GRID_HEIGHT = CELL_SIZE * GRID_SIZE
GRID_MARGIN = 50

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
BLUE = (0, 0, 255)
RED = (255, 0, 0)

# Fonts
FONT = pygame.freetype.SysFont('Arial', 32)
SMALL_FONT = pygame.freetype.SysFont('Arial', 24)

class GameMenu:
    def __init__(self, screen):
        self.screen = screen
        self.username = ""
        self.game_name = ""
        self.password = ""
        self.state = "username"  # States: username, menu, create, join
        self.active_input = None
        self.error_message = ""
        self.error_timer = 0
        
        # Calculate center positions
        center_x = WINDOW_SIZE[0] // 2
        button_width = 200
        button_x = center_x - button_width // 2
        
        # Create buttons
        self.buttons = {
            "menu": [
                {"text": "Create Game", "rect": pygame.Rect(button_x, 200, button_width, 50), "action": lambda: self.set_state("create")},
                {"text": "Join Game", "rect": pygame.Rect(button_x, 300, button_width, 50), "action": lambda: self.set_state("join")},
                {"text": "Quick Match", "rect": pygame.Rect(button_x, 400, button_width, 50), "action": self.quick_match}
            ],
            "create": [
                {"text": "Create", "rect": pygame.Rect(button_x, 400, button_width, 50), "action": self.create_game},
                {"text": "Back", "rect": pygame.Rect(50, 500, 100, 40), "action": lambda: self.set_state("menu")}
            ],
            "join": [
                {"text": "Join", "rect": pygame.Rect(button_x, 400, button_width, 50), "action": self.join_game},
                {"text": "Back", "rect": pygame.Rect(50, 500, 100, 40), "action": lambda: self.set_state("menu")}
            ],
            "username": [
                {"text": "Start", "rect": pygame.Rect(button_x, 400, button_width, 50), "action": self.submit_username}
            ]
        }
        
        # Center input fields
        field_width = 300
        field_x = center_x - field_width // 2
        self.input_fields = {
            "username": pygame.Rect(field_x, 250, field_width, 40),
            "game_name": pygame.Rect(field_x, 200, field_width, 40),
            "password": pygame.Rect(field_x, 300, field_width, 40)
        }
    
    def set_state(self, state):
        self.state = state
        self.error_message = ""
        self.error_timer = 0
    
    def show_error(self, message):
        self.error_message = message
        self.error_timer = 180  # Show for 3 seconds at 60 FPS
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Handle button clicks
            for button in self.buttons.get(self.state, []):
                if button["rect"].collidepoint(event.pos):
                    result = button["action"]()
                    if result:  # Only return if action returned something
                        return result
            
            # Handle input field selection
            self.active_input = None
            if self.state == "username" and self.input_fields["username"].collidepoint(event.pos):
                self.active_input = "username"
            elif self.state in ["create", "join"]:
                if self.input_fields["game_name"].collidepoint(event.pos):
                    self.active_input = "game_name"
                elif self.input_fields["password"].collidepoint(event.pos):
                    self.active_input = "password"
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                # Handle tab navigation between fields
                if self.state == "username":
                    self.active_input = "username"
                elif self.state in ["create", "join"]:
                    if not self.active_input or self.active_input == "password":
                        self.active_input = "game_name"
                    elif self.active_input == "game_name":
                        self.active_input = "password"
            elif event.key == pygame.K_RETURN:
                if self.state == "username":
                    self.submit_username()
                elif self.state == "create":
                    return self.create_game()
                elif self.state == "join":
                    return self.join_game()
            elif event.key == pygame.K_BACKSPACE:
                if self.active_input == "username":
                    self.username = self.username[:-1]
                elif self.active_input == "game_name":
                    self.game_name = self.game_name[:-1]
                elif self.active_input == "password":
                    self.password = self.password[:-1]
            elif event.unicode.isprintable():
                if self.active_input == "username":
                    self.username += event.unicode
                elif self.active_input == "game_name":
                    self.game_name += event.unicode
                elif self.active_input == "password":
                    self.password += event.unicode
        
        return False
    
    def submit_username(self):
        if len(self.username.strip()) < 2:
            self.show_error("Username must be at least 2 characters")
            return False
        self.set_state("menu")
        return False
    
    def create_game(self):
        if len(self.game_name.strip()) < 1:
            self.show_error("Please enter a game name")
            return False
        return ("create", self.game_name.strip(), self.password.strip())
    
    def join_game(self):
        if len(self.game_name.strip()) < 1:
            self.show_error("Please enter a game name")
            return False
        return ("join", self.game_name.strip(), self.password.strip())
    
    def quick_match(self):
        return ("quick_match", "", "")
    
    def draw_button(self, button, hover=False):
        color = LIGHT_GRAY if hover else GRAY
        pygame.draw.rect(self.screen, color, button["rect"])
        pygame.draw.rect(self.screen, BLACK, button["rect"], 2)
        text_surface, text_rect = FONT.render(button["text"], BLACK)
        text_rect.center = button["rect"].center
        self.screen.blit(text_surface, text_rect)
    
    def draw_input_field(self, rect, text, active):
        pygame.draw.rect(self.screen, WHITE, rect)
        pygame.draw.rect(self.screen, BLUE if active else BLACK, rect, 2)
        text_surface, text_rect = FONT.render(text, BLACK)
        text_rect.midleft = (rect.left + 10, rect.centery)
        self.screen.blit(text_surface, text_rect)
    
    def draw(self):
        self.screen.fill(WHITE)
        
        # Draw error message if any
        if self.error_message and self.error_timer > 0:
            text_surface, text_rect = SMALL_FONT.render(self.error_message, RED)
            text_rect.centerx = WINDOW_SIZE[0] // 2
            text_rect.bottom = WINDOW_SIZE[1] - 20
            self.screen.blit(text_surface, text_rect)
            self.error_timer -= 1
        
        if self.state == "username":
            title_surface, title_rect = FONT.render("Enter Your Username", BLACK)
            title_rect.centerx = WINDOW_SIZE[0] // 2
            title_rect.top = 150
            self.screen.blit(title_surface, title_rect)
            
            self.draw_input_field(
                self.input_fields["username"],
                self.username,
                self.active_input == "username"
            )
        
        elif self.state in ["create", "join"]:
            title = "Create Game" if self.state == "create" else "Join Game"
            title_surface, title_rect = FONT.render(title, BLACK)
            title_rect.centerx = WINDOW_SIZE[0] // 2
            title_rect.top = 100
            self.screen.blit(title_surface, title_rect)
            
            name_label, _ = SMALL_FONT.render("Game Name:", BLACK)
            self.screen.blit(name_label, (250, 170))
            
            pass_label, _ = SMALL_FONT.render("Password (optional):", BLACK)
            self.screen.blit(pass_label, (250, 270))
            
            self.draw_input_field(
                self.input_fields["game_name"],
                self.game_name,
                self.active_input == "game_name"
            )
            
            self.draw_input_field(
                self.input_fields["password"],
                "*" * len(self.password),
                self.active_input == "password"
            )
        
        # Draw buttons for current state
        for button in self.buttons.get(self.state, []):
            hover = button["rect"].collidepoint(pygame.mouse.get_pos())
            self.draw_button(button, hover)

@dataclass
class TicTacToeState(GameState):
    """Game state for Tic-tac-toe that works for both client and server"""
    board: List[List[str]] = field(default_factory=lambda: [['' for _ in range(3)] for _ in range(3)])
    current_player: str = 'X'  # X always goes first
    my_symbol: Optional[str] = None  # Used by client to track their symbol
    is_your_turn: bool = False  # Track if it's this client's turn

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
        if update.update_type == UpdateType.GAME_STARTED:
            # Initialize game state from server data
            data = update.data
            self.board = data.get("board", self.board)
            self.current_player = data.get("current_player", self.current_player)
            self.my_symbol = data.get("my_symbol")
            self.is_your_turn = data.get("is_your_turn", False)
            self.game_over = data.get("game_over", False)
            self.winner = data.get("winner")
            self.phase = GamePhase(data.get("phase", "in_game"))
        elif update.update_type == UpdateType.GAME_STATE_UPDATE:
            if "row" in update.data and "col" in update.data:
                # Apply the move
                row, col = update.data["row"], update.data["col"]
                symbol = update.data["symbol"]
                print(f"[TicTacToeState] Applying move: row={row}, col={col}, symbol={symbol}")
                print(f"[TicTacToeState] Board before: {self.board}")
                self.board[row][col] = symbol
                print(f"[TicTacToeState] Board after: {self.board}")
                
                # Update turn information
                self.current_player = 'O' if symbol == 'X' else 'X'
                self.is_your_turn = (self.current_player == self.my_symbol)
                
                # Then check for win/draw
                if self.check_winner():
                    self.winner = symbol  # Use the symbol that just moved
                    self.game_over = True
                    self.phase = GamePhase.END_GAME
                    self.current_player = None
                    self.is_your_turn = False
                elif self.is_draw():
                    self.game_over = True
                    self.winner = None
                    self.phase = GamePhase.END_GAME
                    self.current_player = None
                    self.is_your_turn = False

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
    def __init__(self):
        print("[Client] Initializing TicTacToe game")
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("Tic Tac Toe")
        self.menu = GameMenu(self.screen)
        self.client = None
        self.state = "menu"  # States: menu, connecting, waiting, playing
        self.host = "localhost"  # Default host
        self.port = 8765  # Default port
        
        # Colors
        self.BLACK = BLACK
        self.WHITE = WHITE
        self.GRAY = GRAY
        self.LIGHT_GRAY = LIGHT_GRAY
        
        # Board dimensions
        self.CELL_SIZE = 150
        self.GRID_SIZE = 3
        self.BOARD_SIZE = self.CELL_SIZE * self.GRID_SIZE
        
        # Center the board
        self.board_x = (WINDOW_SIZE[0] - self.BOARD_SIZE) // 2
        self.board_y = (WINDOW_SIZE[1] - self.BOARD_SIZE) // 2

        # Font
        self.font = pygame.freetype.SysFont('Arial', 36)

        # Game state
        self.game_state = None
        
        # Back to menu button
        button_width = 200
        button_height = 50
        button_x = (WINDOW_SIZE[0] - button_width) // 2
        button_y = WINDOW_SIZE[1] - button_height - 20
        self.back_button = {
            "rect": pygame.Rect(button_x, button_y, button_width, button_height),
            "text": "Back to Menu",
            "hover": False
        }
        
        print("[Client] Game window initialized")

    def run(self):
        """Main game loop"""
        clock = pygame.time.Clock()
        
        while True:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    if self.client:
                        self.client.close()
                    pygame.quit()
                    return
                
                if self.state == "menu":
                    action = self.menu.handle_event(event)
                    if isinstance(action, tuple):
                        action_type, game_name, password = action
                        self.state = "connecting"
                        
                        # Initialize client if not done yet
                        if not self.client:
                            self.client = NexusClient(self.host, self.port)
                            self.client.connect()
                        
                        if action_type == "create":
                            print(f"Creating game: {game_name}")
                            self.client.send(Command(CommandType.CREATE_GAME, {
                                "game_name": game_name,
                                "password": password,
                                "player_name": self.menu.username
                            }))
                        elif action_type == "join":
                            print(f"Joining game: {game_name}")
                            self.client.send(Command(CommandType.JOIN_GAME, {
                                "game_name": game_name,
                                "password": password,
                                "player_name": self.menu.username
                            }))
                        else:  # quick_match
                            print("Finding game via matchmaking")
                            self.client.send(Command(CommandType.FIND_GAME, {
                                "player_name": self.menu.username
                            }))
                        self.state = "waiting"
                elif self.state == "playing":
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = event.pos
                        if self.game_state and self.game_state.game_over:
                            # Handle back button click when game is over
                            if self.back_button["rect"].collidepoint(mouse_pos):
                                self.state = "menu"
                                self.game_state = None
                                if self.client:
                                    self.client.close()
                                    self.client = None
                                # Reset menu state to main menu
                                self.menu.set_state("menu")
                                # Clear game-specific fields
                                self.menu.game_name = ""
                                self.menu.password = ""
                        elif self.game_state and self.game_state.is_your_turn:
                            self.handle_click(mouse_pos)
                    elif event.type == pygame.MOUSEMOTION and self.game_state and self.game_state.game_over:
                        # Handle button hover
                        self.back_button["hover"] = self.back_button["rect"].collidepoint(event.pos)
            
            # Process game updates
            if self.client and self.state in ["waiting", "playing"]:
                update = self.client.receive()
                if update:
                    if update.update_type == UpdateType.GAME_STARTED:
                        print("Game started!")
                        self.game_state = TicTacToeState()
                        self.game_state.apply(update)
                        self.state = "playing"
                    elif update.update_type == UpdateType.GAME_STATE_UPDATE:
                        if not self.game_state:
                            self.game_state = TicTacToeState()
                        self.game_state.apply(update)
                    elif update.update_type == UpdateType.ERROR:
                        print(f"Error: {update.data.get('message')}")
                        self.menu.show_error(update.data.get("message", "Unknown error"))
                        self.state = "menu"
            
            self.draw()
            clock.tick(60)

    def handle_click(self, pos: Tuple[int, int]):
        """Handle mouse clicks during the game"""
        if not self.game_state or self.game_state.game_over:
            return
            
        # Convert screen position to grid position
        grid_x = (self.screen.get_width() - self.BOARD_SIZE) // 2
        grid_y = (self.screen.get_height() - self.BOARD_SIZE) // 2
        
        if not (grid_x <= pos[0] <= grid_x + self.BOARD_SIZE and
                grid_y <= pos[1] <= grid_y + self.BOARD_SIZE):
            return
            
        col = (pos[0] - grid_x) // self.CELL_SIZE
        row = (pos[1] - grid_y) // self.CELL_SIZE
        
        # Check if the cell is empty
        if self.game_state.board[row][col]:
            return
            
        # Send move command with the player's symbol
        cmd = Command(CommandType.MAKE_MOVE, {
            "row": row,
            "col": col,
            "symbol": self.game_state.my_symbol
        })
        self.client.send(cmd)

    def draw(self):
        self.screen.fill(self.WHITE)
        
        if self.state == "menu":
            self.menu.draw()
        elif self.state == "connecting":
            text_surface, text_rect = self.font.render("Connecting...", self.BLACK)
            text_rect.center = (self.screen.get_width() // 2, self.screen.get_height() // 2)
            self.screen.blit(text_surface, text_rect)
        elif self.state == "waiting":
            text_surface, text_rect = self.font.render("Waiting for opponent...", self.BLACK)
            text_rect.center = (self.screen.get_width() // 2, self.screen.get_height() // 2)
            self.screen.blit(text_surface, text_rect)
        elif self.state == "playing" and self.game_state:
            # Draw grid
            grid_x = (self.screen.get_width() - self.BOARD_SIZE) // 2
            grid_y = (self.screen.get_height() - self.BOARD_SIZE) // 2
            
            # Draw grid lines
            for i in range(1, self.GRID_SIZE):
                # Vertical lines
                pygame.draw.line(self.screen, self.BLACK,
                               (grid_x + i * self.CELL_SIZE, grid_y),
                               (grid_x + i * self.CELL_SIZE, grid_y + self.BOARD_SIZE), 2)
                # Horizontal lines
                pygame.draw.line(self.screen, self.BLACK,
                               (grid_x, grid_y + i * self.CELL_SIZE),
                               (grid_x + self.BOARD_SIZE, grid_y + i * self.CELL_SIZE), 2)
            
            # Draw X's and O's
            for row in range(self.GRID_SIZE):
                for col in range(self.GRID_SIZE):
                    cell = self.game_state.board[row][col]
                    if cell:
                        x = grid_x + col * self.CELL_SIZE + self.CELL_SIZE // 2
                        y = grid_y + row * self.CELL_SIZE + self.CELL_SIZE // 2
                        text_surface, text_rect = self.font.render(cell, self.BLACK)
                        text_rect.center = (x, y)
                        self.screen.blit(text_surface, text_rect)
            
            # Draw game status
            status_text = ""
            if self.game_state.game_over:
                if self.game_state.winner:
                    status_text = f"Winner: {self.game_state.winner}!"
                else:
                    status_text = "Draw!"
                
                # Draw back to menu button when game is over
                button_color = self.LIGHT_GRAY if self.back_button["hover"] else self.GRAY
                pygame.draw.rect(self.screen, button_color, self.back_button["rect"])
                pygame.draw.rect(self.screen, self.BLACK, self.back_button["rect"], 2)
                text_surface, text_rect = self.font.render(self.back_button["text"], self.BLACK)
                text_rect.center = self.back_button["rect"].center
                self.screen.blit(text_surface, text_rect)
            else:
                # Use is_your_turn from game state to determine whose turn it is
                if self.game_state.is_your_turn:
                    status_text = "Your turn!"
                else:
                    status_text = "Opponent's turn!"
            
            text_surface, text_rect = self.font.render(status_text, self.BLACK)
            text_rect.centerx = self.screen.get_width() // 2
            text_rect.bottom = self.back_button["rect"].top - 20  # Position above the back button
            self.screen.blit(text_surface, text_rect)
        
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
    parser = argparse.ArgumentParser(description='TicTacToe Game')
    parser.add_argument('mode', choices=['server', 'client'], help='Run in server or client mode')
    parser.add_argument('--host', default='localhost', help='Server host (client mode only)')
    parser.add_argument('--port', type=int, default=8765, help='Server port')
    
    args = parser.parse_args()
    
    if args.mode == 'server':
        run_server(args)
    else:
        # Create and run the game directly
        game = TicTacToeGame()
        game.host = args.host
        game.port = args.port
        game.run()

def run_server(args):
    """Run the game in server mode"""
    print(f"[Server] Starting server on port {args.port}")
    server = TicTacToeServer()
    asyncio.run(server.start())


if __name__ == "__main__":
    main() 