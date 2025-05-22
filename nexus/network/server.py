import asyncio
import websockets
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
from nexus.game.gamestate import GameState, GamePhase
from nexus.game.update import Update, UpdateType
from nexus.game.command import Command, CommandType


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

class GameServer(ABC):
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
        
        else:
            game = self.games.get(player.game_id)
            if not game:
                print(f"[Server] Game not found for player {player.name}")
                return
                
            if cmd.command_type == CommandType.SURRENDER:
                print(f"[Server] Player surrendering: {player.name}")
                await self.handle_surrender(game, player)
            else:
                if not self.validate_game_command(game, cmd):
                    return
                await self.handle_game_command(game, player, cmd)

    def validate_game_command(self, game: Game, cmd: Command) -> bool:
        """Validate common game command conditions"""
        if game.game_state.phase != GamePhase.IN_GAME:
            print(f"[Server] Invalid game command: game not in progress")
            return False

        if cmd.command_type != CommandType.MAKE_MOVE:
            print(f"[Server] Invalid command type: {cmd.command_type}")
            return False
            
        return True

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
            game_state=self.create_initial_game_state()
        )
        self.games[name] = game
        player.game_id = name
        print(f"[Server] Game created: {name} by {player.name}")
        
        await self.send_game_update(game, UpdateType.GAME_STATE_UPDATE, 
                                  self.get_player_game_state(game, player))

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

        # Send updates to all players
        for p in game.players:
            await self.send_game_update(game, UpdateType.GAME_STATE_UPDATE, 
                                      self.get_player_game_state(game, p))

    async def find_game(self, player: Player):
        """Add player to matchmaking queue"""
        print(f"[Server] Player {player.name} entered matchmaking")
        self.matchmaking_queue.append(player)
        
        if len(self.matchmaking_queue) >= 2:
            players = self.matchmaking_queue[:2]
            self.matchmaking_queue = self.matchmaking_queue[2:]
            
            game_name = f"match_{len(self.games)}"
            print(f"[Server] Creating matchmaking game {game_name} for {[p.name for p in players]}")
            
            game = Game(
                name=game_name,
                password=None,
                max_players=2,
                players=players,
                game_state=self.create_initial_game_state(),
                is_matchmaking=True
            )
            self.games[game_name] = game
            
            for p in players:
                p.game_id = game_name
                await self.send_game_update(game, UpdateType.GAME_STATE_UPDATE, 
                                          self.get_player_game_state(game, p))

    async def handle_surrender(self, game: Game, player: Player):
        """Handle a player surrendering"""
        if not player.game_id:
            return
            
        game.game_state.phase = GamePhase.END_GAME
        print(f"[Server] Player {player.name} surrendered in game {game.name}")
        
        # Determine winners (everyone except the surrendering player)
        winners = [p.name for p in game.players if p != player]
        
        await self.send_game_update(game, UpdateType.GAME_STATE_UPDATE, {
            "phase": GamePhase.END_GAME,
            "winner": winners[0] if winners else None,
            "reason": "surrender"
        })
        
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
                await self.send_game_update(game, UpdateType.GAME_STATE_UPDATE, 
                                          self.get_player_game_state(game, game.players[0]))

    async def end_game(self, game: Game):
        """Clean up a finished game"""
        print(f"[Server] Ending game {game.name}")
        for player in game.players:
            player.game_id = None
        if game.name in self.games:
            del self.games[game.name]

    async def send_game_update(self, game: Game, update_type: str, data: dict, specific_player: Player = None):
        """Send a game update to all players in a game"""
        if specific_player:
            print(f"[Server] Sending update to {specific_player.name}: {message}")
            player_index = game.players.index(specific_player)
            player_data = game.game_state.get_player_perspective(player_index)
            update = Update(update_type, player_data)
            message = json.dumps(update, default=lambda o: o.__dict__)
            await specific_player.websocket.send(message)
        else:
            print(f"[Server] Broadcasting update to all players in {game.name}")
            for player in game.players:
                player_index = game.players.index(player)
                player_data = game.game_state.get_player_perspective(player_index)
                update = Update(update_type, player_data)
                message = json.dumps(update, default=lambda o: o.__dict__)
                await player.websocket.send(message)

    async def send_error(self, player: Player, error_message: str):
        """Send an error message to a player"""
        print(f"[Server] Sending error to {player.name}: {error_message}")
        await player.websocket.send(json.dumps({
            "type": "error",
            "message": error_message
        }))

    @abstractmethod
    async def handle_game_command(self, game: Game, player: Player, cmd: Command):
        """Handle game-specific commands - must be implemented by subclass"""
        pass

    @abstractmethod
    def create_initial_game_state(self) -> GameState:
        """Create the initial game state - must be implemented by subclass"""
        pass

    @abstractmethod
    def get_player_game_state(self, game: Game, player: Player) -> dict:
        """Get the game state from a specific player's perspective - must be implemented by subclass"""
        pass

if __name__ == "__main__":
    server = GameServer()
    asyncio.run(server.start())

    