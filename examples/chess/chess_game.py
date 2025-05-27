import asyncio
import pygame
import chess
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
import os

# Initialize Pygame
pygame.init()
pygame.freetype.init()

# Constants
WINDOW_SIZE = (800, 800)
BOARD_SIZE = 600
SQUARE_SIZE = BOARD_SIZE // 8

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_SQUARE = (181, 136, 99)  # Brown
LIGHT_SQUARE = (240, 217, 181)  # Light brown
HIGHLIGHT = (124, 252, 0)  # Light green for legal moves
SELECTED = (255, 255, 0, 128)  # Semi-transparent yellow for selected piece

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
        pygame.draw.rect(self.screen, (0, 0, 255) if active else BLACK, rect, 2)
        text_surface, text_rect = FONT.render(text, BLACK)
        text_rect.midleft = (rect.left + 10, rect.centery)
        self.screen.blit(text_surface, text_rect)
    
    def draw(self):
        self.screen.fill(WHITE)
        
        # Draw error message if any
        if self.error_message and self.error_timer > 0:
            text_surface, text_rect = SMALL_FONT.render(self.error_message, (255, 0, 0))
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
class ChessGameState(GameState):
    """Game state for Chess that works for both client and server"""
    board: chess.Board = field(default_factory=chess.Board)
    current_player: str = 'white'  # white always goes first
    my_color: Optional[str] = None  # Used by client to track their color
    is_your_turn: bool = False
    selected_square: Optional[int] = None  # Currently selected square (0-63)
    legal_moves: List[int] = field(default_factory=list)  # Legal moves for selected piece

    def get_player_perspective(self, player_index: int) -> Dict[str, Any]:
        """Get the game state from a specific player's perspective"""
        state = super().get_player_perspective(player_index)
        player_color = "white" if player_index == 0 else "black"
        state.update({
            "board": self.board.fen(),
            "current_player": self.current_player,
            "winner": self.winner,
            "my_color": player_color,
            "is_your_turn": (self.current_player == player_color)
        })
        return state

    def is_valid(self, cmd: Command, player_index: int) -> Tuple[bool, str]:
        """Validate if a move is valid"""
        # Get player's color
        player_color = "white" if player_index == 0 else "black"
        
        # Verify it's the player's turn
        if player_color != self.current_player:
            return False, f"Not your turn - it's {self.current_player}'s turn"

        # Validate move
        try:
            move = chess.Move.from_uci(cmd.data["move"])
        except (KeyError, ValueError):
            return False, "Invalid command: missing or invalid move"

        # Check if move is legal
        if move not in self.board.legal_moves:
            return False, "Illegal move"

        return True, ""

    def apply(self, update: Update) -> None:
        """Apply an update to the game state"""
        if update.update_type == UpdateType.GAME_STARTED:
            # Initialize game state from server data
            data = update.data
            self.board = chess.Board(data.get("board", chess.STARTING_FEN))
            self.current_player = data.get("current_player", "white")
            self.my_color = data.get("my_color")
            self.is_your_turn = data.get("is_your_turn", False)
            self.game_over = data.get("game_over", False)
            self.winner = data.get("winner")
            self.phase = GamePhase(data.get("phase", "in_game"))
        elif update.update_type == UpdateType.GAME_STATE_UPDATE:
            if "move" in update.data:
                # Apply the move
                move = chess.Move.from_uci(update.data["move"])
                self.board.push(move)
                
                # Update turn information
                self.current_player = "black" if self.current_player == "white" else "white"
                self.is_your_turn = (self.current_player == self.my_color)
                
                # Check for game end conditions
                if self.board.is_checkmate():
                    self.game_over = True
                    self.winner = "black" if self.current_player == "white" else "white"
                    self.phase = GamePhase.END_GAME
                    self.current_player = None
                    self.is_your_turn = False
                elif self.board.is_stalemate() or self.board.is_insufficient_material():
                    self.game_over = True
                    self.winner = None  # Draw
                    self.phase = GamePhase.END_GAME
                    self.current_player = None
                    self.is_your_turn = False

class ChessGame(NexusGame[ChessGameState]):
    def __init__(self):
        print("[Client] Initializing Chess game")
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("Chess")
        self.menu = GameMenu(self.screen)
        self.client = None
        self.state = "menu"  # States: menu, connecting, waiting, playing
        self.host = "localhost"  # Default host
        self.port = 8765  # Default port
        
        # Load piece images
        self.pieces = {}
        piece_size = SQUARE_SIZE - 10  # Slightly smaller than square size
        piece_map = {
            'pawn': 'p',
            'rook': 'r',
            'knight': 'n',
            'bishop': 'b',
            'queen': 'q',
            'king': 'k'
        }
        color_map = {
            'white': 'w',
            'black': 'b'
        }
        for color in ['white', 'black']:
            for piece in ['pawn', 'rook', 'knight', 'bishop', 'queen', 'king']:
                image_path = os.path.join('assets', 'chess', f"{color_map[color]}_{piece_map[piece]}.svg")
                try:
                    image = pygame.image.load(image_path)
                    self.pieces[f"{color}_{piece}"] = pygame.transform.scale(image, (piece_size, piece_size))
                except pygame.error:
                    print(f"Could not load piece image: {image_path}")
                    # Create a fallback piece representation
                    surface = pygame.Surface((piece_size, piece_size), pygame.SRCALPHA)
                    pygame.draw.circle(surface, (255, 0, 0, 128), (piece_size//2, piece_size//2), piece_size//2)
                    self.pieces[f"{color}_{piece}"] = surface

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

        # Game state
        self.game_state = None
        print("[Client] Game window initialized")

    def get_square_at_pos(self, pos: Tuple[int, int]) -> Optional[int]:
        """Convert screen position to board square index (0-63)"""
        board_x = (WINDOW_SIZE[0] - BOARD_SIZE) // 2
        board_y = (WINDOW_SIZE[1] - BOARD_SIZE) // 2
        
        if not (board_x <= pos[0] <= board_x + BOARD_SIZE and
                board_y <= pos[1] <= board_y + BOARD_SIZE):
            return None
            
        file = (pos[0] - board_x) // SQUARE_SIZE
        rank = 7 - (pos[1] - board_y) // SQUARE_SIZE  # Flip rank for white's perspective
        
        if self.game_state and self.game_state.my_color == "black":
            file = 7 - file
            rank = 7 - rank
        
        return rank * 8 + file

    def get_piece_at_square(self, square: int) -> Optional[chess.Piece]:
        """Get the piece at the given square"""
        if not self.game_state:
            return None
        return self.game_state.board.piece_at(square)

    def handle_click(self, pos: Tuple[int, int]):
        """Handle mouse clicks during the game"""
        if not self.game_state or self.game_state.game_over or not self.game_state.is_your_turn:
            return
            
        clicked_square = self.get_square_at_pos(pos)
        if clicked_square is None:
            return

        if self.game_state.selected_square is None:
            # Select piece if it's ours
            piece = self.get_piece_at_square(clicked_square)
            if piece and piece.color == (self.game_state.my_color == "white"):
                self.game_state.selected_square = clicked_square
                # Calculate legal moves for this piece
                self.game_state.legal_moves = [
                    move.to_square
                    for move in self.game_state.board.legal_moves
                    if move.from_square == clicked_square
                ]
        else:
            # Try to make a move
            if clicked_square in self.game_state.legal_moves:
                move = chess.Move(self.game_state.selected_square, clicked_square)
                # Add promotion if needed
                if self.game_state.board.piece_at(self.game_state.selected_square).piece_type == chess.PAWN:
                    if (self.game_state.my_color == "white" and clicked_square // 8 == 7) or \
                       (self.game_state.my_color == "black" and clicked_square // 8 == 0):
                        move.promotion = chess.QUEEN  # Always promote to queen for simplicity
                
                # Send move command
                self.client.send(Command(CommandType.MAKE_MOVE, {
                    "move": move.uci()
                }))
            
            # Clear selection
            self.game_state.selected_square = None
            self.game_state.legal_moves = []

    def draw_board(self):
        """Draw the chess board and pieces"""
        board_x = (WINDOW_SIZE[0] - BOARD_SIZE) // 2
        board_y = (WINDOW_SIZE[1] - BOARD_SIZE) // 2
        
        # Draw squares
        for rank in range(8):
            for file in range(8):
                x = board_x + file * SQUARE_SIZE
                y = board_y + rank * SQUARE_SIZE
                color = LIGHT_SQUARE if (rank + file) % 2 == 0 else DARK_SQUARE
                pygame.draw.rect(self.screen, color, (x, y, SQUARE_SIZE, SQUARE_SIZE))
                
                # Get board coordinates based on perspective
                board_file = file
                board_rank = 7 - rank
                if self.game_state and self.game_state.my_color == "black":
                    board_file = 7 - file
                    board_rank = rank
                
                square = board_rank * 8 + board_file
                
                # Draw selection highlight
                if self.game_state and square == self.game_state.selected_square:
                    highlight = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                    pygame.draw.rect(highlight, SELECTED, highlight.get_rect())
                    self.screen.blit(highlight, (x, y))
                
                # Draw move highlights
                if self.game_state and square in self.game_state.legal_moves:
                    highlight = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                    pygame.draw.rect(highlight, HIGHLIGHT, highlight.get_rect())
                    self.screen.blit(highlight, (x, y))
                
                # Draw piece
                if self.game_state:
                    piece = self.game_state.board.piece_at(square)
                    if piece:
                        color = "white" if piece.color else "black"
                        piece_name = {
                            chess.PAWN: "pawn",
                            chess.ROOK: "rook",
                            chess.KNIGHT: "knight",
                            chess.BISHOP: "bishop",
                            chess.QUEEN: "queen",
                            chess.KING: "king"
                        }[piece.piece_type]
                        piece_image = self.pieces[f"{color}_{piece_name}"]
                        piece_x = x + (SQUARE_SIZE - piece_image.get_width()) // 2
                        piece_y = y + (SQUARE_SIZE - piece_image.get_height()) // 2
                        self.screen.blit(piece_image, (piece_x, piece_y))

    def draw(self):
        self.screen.fill(WHITE)
        
        if self.state == "menu":
            self.menu.draw()
        elif self.state == "connecting":
            text_surface, text_rect = FONT.render("Connecting...", BLACK)
            text_rect.center = (self.screen.get_width() // 2, self.screen.get_height() // 2)
            self.screen.blit(text_surface, text_rect)
        elif self.state == "waiting":
            text_surface, text_rect = FONT.render("Waiting for opponent...", BLACK)
            text_rect.center = (self.screen.get_width() // 2, self.screen.get_height() // 2)
            self.screen.blit(text_surface, text_rect)
        elif self.state == "playing" and self.game_state:
            self.draw_board()
            
            # Draw game status
            status_text = ""
            if self.game_state.game_over:
                if self.game_state.winner:
                    status_text = f"Winner: {self.game_state.winner}!"
                else:
                    status_text = "Draw!"
                
                # Draw back to menu button
                button_color = LIGHT_GRAY if self.back_button["hover"] else GRAY
                pygame.draw.rect(self.screen, button_color, self.back_button["rect"])
                pygame.draw.rect(self.screen, BLACK, self.back_button["rect"], 2)
                text_surface, text_rect = FONT.render(self.back_button["text"], BLACK)
                text_rect.center = self.back_button["rect"].center
                self.screen.blit(text_surface, text_rect)
            else:
                if self.game_state.is_your_turn:
                    status_text = "Your turn!"
                else:
                    status_text = "Opponent's turn!"
            
            text_surface, text_rect = FONT.render(status_text, BLACK)
            text_rect.centerx = self.screen.get_width() // 2
            text_rect.bottom = self.back_button["rect"].top - 20 if self.game_state.game_over else self.screen.get_height() - 20
            self.screen.blit(text_surface, text_rect)
        
        pygame.display.flip()

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
                        else:
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
                        self.game_state = ChessGameState()
                        self.game_state.apply(update)
                        self.state = "playing"
                    elif update.update_type == UpdateType.GAME_STATE_UPDATE:
                        if not self.game_state:
                            self.game_state = ChessGameState()
                        self.game_state.apply(update)
                    elif update.update_type == UpdateType.ERROR:
                        print(f"Error: {update.data.get('message')}")
                        self.menu.show_error(update.data.get("message", "Unknown error"))
                        self.state = "menu"
            
            self.draw()
            clock.tick(60)

class ChessServer(NexusServer):
    def create_initial_game_state(self, players: List[NexusPlayer]) -> ChessGameState:
        """Create the initial game state for a new game"""
        return ChessGameState(players)

def main():
    parser = argparse.ArgumentParser(description='Chess Game')
    parser.add_argument('mode', choices=['server', 'client'], help='Run in server or client mode')
    parser.add_argument('--host', default='localhost', help='Server host (client mode only)')
    parser.add_argument('--port', type=int, default=8765, help='Server port')
    
    args = parser.parse_args()
    
    if args.mode == 'server':
        run_server(args)
    else:
        # Create and run the game directly
        game = ChessGame()
        game.host = args.host
        game.port = args.port
        game.run()

def run_server(args):
    """Run the game in server mode"""
    print(f"[Server] Starting server on port {args.port}")
    server = ChessServer()
    asyncio.run(server.start())

if __name__ == "__main__":
    main() 