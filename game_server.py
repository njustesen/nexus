import asyncio
import websockets
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from game_state import GameState, GamePhase
from game_update import GameUpdate, UpdateType
from command import Command, CommandType


@dataclass
class Player:
    websocket: websockets.WebSocketServerProtocol
    game_id: Optional[str] = None
    name: str = ""

@dataclass
class Game:
    name: str
    password: Optional[str]
    max_players: int
    players: List[Player]
    game_state: GameState
    is_matchmaking: bool = False

class WebSocketGameServer:
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.games: Dict[str, Game] = {}
        self.players: Dict[websockets.WebSocketServerProtocol, Player] = {}
        self.matchmaking_queue: List[Player] = []
        print(f"[Server] Initialized on {host}:{port}")

    async def start(self):
        """Start the WebSocket server"""
        print("[Server] Starting server...")
        async with websockets.serve(self.handle_connection, self.host, self.port):
            print(f"[Server] Listening on ws://{self.host}:{self.port}")
            await asyncio.Future()  # run forever

    async def handle_connection(self, websocket: websockets.WebSocketServerProtocol):
        """Handle a new WebSocket connection"""
        print(f"[Server] New connection from {websocket.remote_address}")
        player = Player(websocket=websocket)
        self.players[websocket] = player

        try:
            async for message in websocket:
                print(f"[Server] Received message: {message}")
                try:
                    cmd = Command(**json.loads(message))
                    print(f"[Server] Processing command: {cmd.command_type}")
                    await self.handle_command(player, cmd)
                except json.JSONDecodeError:
                    print(f"[Server] Error: Invalid JSON message: {message}")
                except Exception as e:
                    print(f"[Server] Error processing command: {str(e)}")
                    await self.send_error(player, f"Error: {str(e)}")
        except websockets.exceptions.ConnectionClosed:
            print(f"[Server] Client disconnected: {websocket.remote_address}")
            await self.handle_disconnect(player)
        finally:
            del self.players[websocket]

    async def handle_command(self, player: Player, cmd: Command):
        """Handle incoming commands from players"""
        print(f"[Server] Handling command {cmd.command_type} from player {player.name}")
        
        if cmd.command_type == "create_game":
            print(f"[Server] Creating game: {cmd.data}")
            await self.create_game(player, cmd.data["name"], cmd.data.get("password"), 
                                 cmd.data.get("max_players", 2))
            player.name = cmd.data.get("player_name", "")
        
        elif cmd.command_type == "join_game":
            print(f"[Server] Joining game: {cmd.data}")
            await self.join_game(player, cmd.data["name"], cmd.data.get("password"))
            player.name = cmd.data.get("player_name", "")
        
        elif cmd.command_type == "find_game":
            print(f"[Server] Finding game for player: {cmd.data}")
            player.name = cmd.data.get("player_name", "")
            await self.find_game(player)
        
        elif cmd.command_type == "surrender":
            print(f"[Server] Player surrendering: {player.name}")
            await self.handle_surrender(player)
        
        elif cmd.command_type == "make_move":
            print(f"[Server] Processing move: {cmd.data}")
            await self.handle_game_command(player, cmd)
        
        elif player.game_id and cmd.command_type in [
            CommandType.MOVE_UP, CommandType.MOVE_DOWN, 
            CommandType.MOVE_LEFT, CommandType.MOVE_RIGHT,
            CommandType.SHOOT, CommandType.USE_ITEM,
            CommandType.DROP_ITEM, CommandType.PICK_UP_ITEM,
            CommandType.MAKE_MOVE  # Add make_move to valid commands
        ]:
            await self.handle_game_command(player, cmd)

    async def create_game(self, player: Player, name: str, password: Optional[str] = None, max_players: int = 2):
        """Create a new game"""
        if name in self.games:
            print(f"[Server] Game creation failed: {name} already exists")
            await self.send_error(player, "Game name already exists")
            return

        game = Game(
            name=name,
            password=password,
            max_players=max_players,
            players=[player],
            game_state=GameState()
        )
        self.games[name] = game
        player.game_id = name
        print(f"[Server] Game created: {name} by {player.name}")
        
        await self.send_game_update(game, UpdateType.GAME_STATE_UPDATE, {
            "phase": GamePhase.LOBBY,
            "players": [p.name for p in game.players],
            "your_symbol": "X"  # First player is always X
        })

    async def join_game(self, player: Player, game_name: str, password: Optional[str] = None):
        """Join an existing game"""
        game = self.games.get(game_name)
        if not game:
            print(f"[Server] Join failed: Game {game_name} not found")
            await self.send_error(player, "Game not found")
            return

        if game.password and game.password != password:
            print(f"[Server] Join failed: Invalid password for game {game_name}")
            await self.send_error(player, "Invalid password")
            return

        if len(game.players) >= game.max_players:
            print(f"[Server] Join failed: Game {game_name} is full")
            await self.send_error(player, "Game is full")
            return

        game.players.append(player)
        player.game_id = game_name
        print(f"[Server] Player {player.name} joined game {game_name}")

        # If game is now full, start it
        if len(game.players) == game.max_players:
            game.game_state.phase = GamePhase.IN_GAME
            print(f"[Server] Game {game_name} starting with {len(game.players)} players")
            
        # Send individual updates to each player with their symbols
        for p in game.players:
            symbol = "X" if p == game.players[0] else "O"
            await self.send_game_update(game, UpdateType.GAME_STATE_UPDATE, {
                "phase": game.game_state.phase,
                "players": [pl.name for pl in game.players],
                "your_symbol": symbol,
                "current_player": "X",  # X always goes first
                "board": game.game_state.board if hasattr(game.game_state, 'board') else [['' for _ in range(3)] for _ in range(3)]
            }, specific_player=p)

    async def find_game(self, player: Player):
        """Add player to matchmaking queue"""
        print(f"[Server] Player {player.name} entered matchmaking")
        self.matchmaking_queue.append(player)
        
        # Check if we can create a match
        if len(self.matchmaking_queue) >= 2:
            players = self.matchmaking_queue[:2]
            self.matchmaking_queue = self.matchmaking_queue[2:]
            
            # Create a new game for these players
            game_name = f"match_{len(self.games)}"
            print(f"[Server] Creating matchmaking game {game_name} for {[p.name for p in players]}")
            
            game = Game(
                name=game_name,
                password=None,
                max_players=2,
                players=players,
                game_state=GameState(),
                is_matchmaking=True
            )
            self.games[game_name] = game
            
            for i, p in enumerate(players):
                p.game_id = game_name
                symbol = "X" if i == 0 else "O"
                await self.send_game_update(game, UpdateType.GAME_STATE_UPDATE, {
                    "phase": GamePhase.IN_GAME,
                    "players": [pl.name for pl in players],
                    "your_symbol": symbol,
                    "current_player": "X",
                    "board": [['' for _ in range(3)] for _ in range(3)]
                }, specific_player=p)

    async def handle_game_command(self, player: Player, cmd: Command):
        """Handle a game-specific command"""
        game = self.games.get(player.game_id)
        if not game or game.game_state.phase != GamePhase.IN_GAME:
            print(f"[Server] Invalid game command: game not found or not in progress")
            return

        if cmd.command_type == "make_move":
            row, col = cmd.data["row"], cmd.data["col"]
            symbol = cmd.data["symbol"]
            board = game.game_state.board
            
            # Validate move
            if not (0 <= row < 3 and 0 <= col < 3) or board[row][col]:
                print(f"[Server] Invalid move: {row}, {col}")
                return
            
            # Make move
            board[row][col] = symbol
            print(f"[Server] Move made: {symbol} at {row}, {col}")
            
            # Check for win
            winner = self.check_winner(board)
            is_draw = all(all(cell != '' for cell in row) for row in board)
            
            # Prepare update
            next_player = "O" if symbol == "X" else "X"
            update_data = {
                "board": board,
                "current_player": next_player if not winner and not is_draw else None
            }
            
            if winner:
                update_data["phase"] = GamePhase.END_GAME
                update_data["winner"] = winner
                print(f"[Server] Game ended: {winner} wins!")
            elif is_draw:
                update_data["phase"] = GamePhase.END_GAME
                print(f"[Server] Game ended: Draw!")
            
            await self.send_game_update(game, UpdateType.GAME_STATE_UPDATE, update_data)

    def check_winner(self, board):
        # Check rows, columns and diagonals
        for i in range(3):
            if board[i][0] == board[i][1] == board[i][2] != '':
                return board[i][0]
            if board[0][i] == board[1][i] == board[2][i] != '':
                return board[0][i]
        if board[0][0] == board[1][1] == board[2][2] != '':
            return board[0][0]
        if board[0][2] == board[1][1] == board[2][0] != '':
            return board[0][2]
        return None

    async def handle_surrender(self, player: Player):
        """Handle a player surrendering"""
        if not player.game_id:
            return
            
        game = self.games[player.game_id]
        game.game_state.phase = GamePhase.END_GAME
        print(f"[Server] Player {player.name} surrendered in game {game.name}")
        
        # Determine winners (everyone except the surrendering player)
        winners = [p.name for p in game.players if p != player]
        
        await self.send_game_update(game, UpdateType.GAME_STATE_UPDATE, {
            "phase": GamePhase.END_GAME,
            "winner": winners[0] if winners else None,
            "reason": "surrender"
        })
        
        # Clean up the game
        await self.end_game(game)

    async def handle_disconnect(self, player: Player):
        """Handle a player disconnecting"""
        print(f"[Server] Player {player.name} disconnected")
        if player in self.matchmaking_queue:
            self.matchmaking_queue.remove(player)
            print(f"[Server] Removed {player.name} from matchmaking queue")
            
        if player.game_id:
            game = self.games[player.game_id]
            game.players.remove(player)
            print(f"[Server] Removed {player.name} from game {game.name}")
            
            if len(game.players) < 2:
                await self.end_game(game)
            else:
                await self.send_game_update(game, UpdateType.GAME_STATE_UPDATE, {
                    "players": [p.name for p in game.players]
                })

    async def end_game(self, game: Game):
        """Clean up a finished game"""
        print(f"[Server] Ending game {game.name}")
        for player in game.players:
            player.game_id = None
        if game.name in self.games:
            del self.games[game.name]

    async def send_game_update(self, game: Game, update_type: str, data: dict, specific_player: Player = None):
        """Send a game update to all players in a game"""
        update = GameUpdate(update_type, data)
        message = json.dumps(update, default=lambda o: o.__dict__)
        
        if specific_player:
            print(f"[Server] Sending update to {specific_player.name}: {message}")
            await specific_player.websocket.send(message)
        else:
            print(f"[Server] Broadcasting update to all players in {game.name}: {message}")
            await asyncio.gather(
                *(player.websocket.send(message) for player in game.players)
            )

    async def send_error(self, player: Player, error_message: str):
        """Send an error message to a player"""
        print(f"[Server] Sending error to {player.name}: {error_message}")
        await player.websocket.send(json.dumps({
            "type": "error",
            "message": error_message
        }))

if __name__ == "__main__":
    server = WebSocketGameServer()
    asyncio.run(server.start())

    