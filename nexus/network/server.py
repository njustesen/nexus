import asyncio
import websockets
import json
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from nexus.game.gamestate import GameState, GamePhase
from nexus.network.update import Update, UpdateType
from nexus.network.command import Command, CommandType
from nexus.network.player import NexusPlayer
from nexus.network.game import NexusGame

@dataclass
class ConnectionManager:
    """Manages the bidirectional mapping between WebSocket connections and players"""
    socket_to_player: Dict[websockets.WebSocketServerProtocol, NexusPlayer] = field(default_factory=dict)
    player_to_socket: Dict[str, websockets.WebSocketServerProtocol] = field(default_factory=dict)

    def add_connection(self, socket: websockets.WebSocketServerProtocol, player: NexusPlayer) -> None:
        """Add a new socket-player connection"""
        print(f"[ConnectionManager] Adding connection for player {player.id} with game_id: {player.game_id}")
        self.socket_to_player[socket] = player
        self.player_to_socket[player.id] = socket

    def remove_connection(self, socket: websockets.WebSocketServerProtocol) -> Optional[NexusPlayer]:
        """Remove a connection by socket and return the associated player if any"""
        if player := self.socket_to_player.get(socket):
            print(f"[ConnectionManager] Removing connection for player {player.id} with game_id: {player.game_id}")
            del self.socket_to_player[socket]
            del self.player_to_socket[player.id]
            return player
        return None

    def get_player(self, socket: websockets.WebSocketServerProtocol) -> Optional[NexusPlayer]:
        """Get player associated with a socket"""
        player = self.socket_to_player.get(socket)
        print(f"[ConnectionManager] Getting player for socket: {player.id if player else None} with game_id: {player.game_id if player else None}")
        return player

    def get_socket(self, player_id: str) -> Optional[websockets.WebSocketServerProtocol]:
        """Get socket associated with a player ID"""
        socket = self.player_to_socket.get(player_id)
        print(f"[ConnectionManager] Getting socket for player: {player_id}")
        return socket

class NexusServer(ABC):
    """Base server class for the Nexus framework"""
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.games: Dict[str, NexusGame] = {}
        self.connections = ConnectionManager()
        self.matchmaking_queue: List[str] = []  # List of player IDs
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
        player_id = str(uuid.uuid4())
        player = NexusPlayer(id=player_id)
        print(f"[Server] Created new player with id: {player_id}")
        self.connections.add_connection(websocket, player)

        try:
            async for message in websocket:
                print(f"[Server] Received message: {message}")
                try:
                    # Parse JSON and create Command using from_dict
                    data = json.loads(message)
                    cmd = Command.from_dict(data)
                    print(f"[Server] Processing command: {cmd.command_type}")
                    # Get the current player state from connections
                    current_player = self.connections.get_player(websocket)
                    print(f"[Server] Current player state - id: {current_player.id}, game_id: {current_player.game_id}")
                    await self.handle_command(current_player, cmd)
                except json.JSONDecodeError:
                    print(f"[Server] Error: Invalid JSON message: {message}")
                except Exception as e:
                    print(f"[Server] Error processing command: {str(e)}")
                    await self.send_error(player, f"Error: {str(e)}")
        except websockets.exceptions.ConnectionClosed:
            print(f"[Server] Client disconnected: {websocket.remote_address}")
            await self.handle_disconnect(player)
        finally:
            self.connections.remove_connection(websocket)

    async def handle_command(self, player: NexusPlayer, cmd: Command):
        """Handle incoming commands from players"""
        print(f"[Server] Handling command {cmd.command_type} from player {player.name}")
        
        if cmd.command_type == CommandType.CREATE_GAME:
            print(f"[Server] Creating game: {cmd.data}")
            # Create new player with updated name but preserve game_id
            new_player = NexusPlayer(
                id=player.id,
                name=cmd.data.get("player_name", ""),
                game_id=player.game_id
            )
            # Update our mappings
            websocket = self.connections.get_socket(player.id)
            self.connections.add_connection(websocket, new_player)
            await self.create_game(new_player, cmd.data["game_name"], cmd.data.get("password"), 
                                 cmd.data.get("max_players", 2))
        
        elif cmd.command_type == CommandType.JOIN_GAME:
            print(f"[Server] Joining game: {cmd.data}")
            new_player = NexusPlayer(
                id=player.id,
                name=cmd.data.get("player_name", ""),
                game_id=player.game_id
            )
            websocket = self.connections.get_socket(player.id)
            self.connections.add_connection(websocket, new_player)
            await self.join_game(new_player, cmd.data["game_name"], cmd.data.get("password"))
        
        elif cmd.command_type == CommandType.FIND_GAME:
            print(f"[Server] Finding game for player: {cmd.data}")
            new_player = NexusPlayer(
                id=player.id,
                name=cmd.data.get("player_name", ""),
                game_id=player.game_id
            )
            websocket = self.connections.get_socket(player.id)
            self.connections.add_connection(websocket, new_player)
            await self.find_game(new_player)
        
        else:
            game = self.games.get(player.game_id) if player.game_id else None
            if not game:
                print(f"[Server] Game not found for player {player.name} with game_id {player.game_id}")
                return
                
            if cmd.command_type == CommandType.SURRENDER:
                print(f"[Server] Player surrendering: {player.name}")
                await self.handle_surrender(game, player)
            else:
                if not self.validate_game_command(game, cmd):
                    return
                await self.handle_game_command(game, player, cmd)

    def validate_game_command(self, game: NexusGame, cmd: Command) -> bool:
        """Validate common game command conditions"""
        if game.phase != GamePhase.IN_GAME:
            print(f"[Server] Invalid game command: game not in progress")
            return False

        if cmd.command_type != CommandType.MAKE_MOVE:
            print(f"[Server] Invalid command type: {cmd.command_type}")
            return False
            
        return True

    async def create_game(self, player: NexusPlayer, name: str, password: Optional[str] = None, max_players: int = 2):
        """Create a new game"""
        if name in self.games:
            print(f"[Server] Game creation failed: {name} already exists")
            await self.send_error(player, "Game name already exists")
            return

        game = NexusGame(
            name=name,
            password=password,
            max_players=max_players,
            players=[player],
            game_state=None,
            phase=GamePhase.LOBBY
        )
        self.games[name] = game
        player.game_id = name
        print(f"[Server] Game created: {name} by {player.name}")
        
        update = Update(UpdateType.GAME_CREATED, {})
        await self.send_game_update(game, update, player)

    async def join_game(self, player: NexusPlayer, game_name: str, password: Optional[str] = None):
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
            game.game_state = self.create_initial_game_state(game.players)
            game.phase = GamePhase.IN_GAME
            print(f"[Server] Game {game_name} starting with {len(game.players)} players")

        # Send updates to all players
        for p in game.players:
            state_data = self.get_player_game_state(game, p)
            update = Update(UpdateType.GAME_STARTED, state_data)
            await self.send_game_update(game, update, p)

    async def find_game(self, player: NexusPlayer):
        """Add player to matchmaking queue"""
        print(f"[Server] Player {player.name} entered matchmaking")
        self.matchmaking_queue.append(player.id)
        
        if len(self.matchmaking_queue) >= 2:
            print(f"[Server] Found enough players for a match")
            players = []
            for pid in self.matchmaking_queue[:2]:
                socket = self.connections.get_socket(pid)
                player = self.connections.get_player(socket)
                print(f"[Server] Retrieved player from connections: {player.name} (id: {player.id})")
                players.append(player)
            self.matchmaking_queue = self.matchmaking_queue[2:]
            
            game_name = f"match_{len(self.games)}"
            print(f"[Server] Creating matchmaking game {game_name}")
            
            game = NexusGame(
                name=game_name,
                max_players=2,
                phase=GamePhase.IN_GAME,
                players=players,
                game_state=self.create_initial_game_state(players),
                is_matchmaking=True
            )
            self.games[game_name] = game
            
            # Update all players with their game_id
            for p in players:
                # Create new player instance with game_id
                updated_player = NexusPlayer(
                    id=p.id,
                    name=p.name,
                    game_id=game_name
                )
                print(f"[Server] Created updated player: {updated_player.name} (id: {updated_player.id}, game_id: {updated_player.game_id})")
                
                # Update the connection mapping
                socket = self.connections.get_socket(p.id)
                self.connections.add_connection(socket, updated_player)
                print(f"[Server] Updated connection mapping for player")
                
                # Send game state
                state_data = self.get_player_game_state(game, updated_player)
                update = Update(UpdateType.GAME_STARTED, state_data)
                await self.send_game_update(game, update, updated_player)

    async def handle_surrender(self, game: NexusGame, player: NexusPlayer):
        """Handle a player surrendering"""
        if not player.game_id:
            return
            
        game.phase = GamePhase.END_GAME
        print(f"[Server] Player {player.name} surrendered in game {game.name}")
        
        # Determine winners (everyone except the surrendering player)
        winners = [p.name for p in game.players if p != player]
        
        update = Update(UpdateType.GAME_OVER, {
            "winner": winners[0] if winners else None,
            "reason": "surrender"
        })
        await self.send_game_update(game, update, player)
        
        await self.end_game(game)

    async def handle_disconnect(self, player: NexusPlayer):
        """Handle a player disconnecting"""
        print(f"[Server] Player {player.name} disconnected")
        if player.id in self.matchmaking_queue:
            self.matchmaking_queue.remove(player.id)
            print(f"[Server] Removed {player.name} from matchmaking queue")
            
        if player.game_id:
            game = self.games[player.game_id]
            game.players.remove(player)
            print(f"[Server] Removed {player.name} from game {game.name}")
            
            if len(game.players) < 2:
                await self.end_game(game)
            else:
                # Send update to remaining players
                state_data = self.get_player_game_state(game, game.players[0])
                update = Update(UpdateType.GAME_STATE_UPDATE, state_data)
                await self.send_game_update(game, update, game.players[0])

    async def end_game(self, game: NexusGame):
        """Clean up a finished game"""
        print(f"[Server] Ending game {game.name}")
        for player in game.players:
            player.game_id = None
        if game.name in self.games:
            del self.games[game.name]

    def get_player_game_state(self, game: NexusGame, player: NexusPlayer) -> dict:
        """Get the game state from a specific player's perspective"""
        player_index = game.players.index(player)
        return game.game_state.get_player_perspective(player_index)

    async def handle_game_command(self, game: NexusGame, player: NexusPlayer, cmd: Command):
        """Handle game-specific commands"""
        print(f"[Server] Handling game command from {player.name} in game {game.name}")
        # Get player index and validate command
        player_index = game.players.index(player)
        is_valid, error_message = game.game_state.is_valid(cmd, player_index)
        if not is_valid:
            print(f"[Server] Invalid command from {player.name}: {error_message}")
            await self.send_error(player, error_message)
            return

        # Create and apply the update
        update = Update(UpdateType.GAME_STATE_UPDATE, cmd.data)
        game.game_state.apply(update)
        await self.send_game_update(game, update)
        
        # Log game end conditions if any
        if game.game_state.game_over:
            game.phase = GamePhase.END_GAME
            
            if game.game_state.winner:
                print(f"[Server] Game ended: {game.game_state.winner} wins!")
                # Then send game over update
                game_over_update = Update(UpdateType.GAME_OVER, {
                    "winner": game.game_state.winner,
                    "reason": "win"
                })
                await self.send_game_update(game, game_over_update)
            else:
                print(f"[Server] Game ended: Draw!")
                # Send game over update
                game_over_update = Update(UpdateType.GAME_OVER, {
                    "winner": None,
                    "reason": "draw"
                })
                await self.send_game_update(game, game_over_update)
        #else:
            # Send regular state update
            #print(f"[Server] Broadcasting updated game state to all players")
            #await self.send_game_update(game, update)

    async def send_game_update(self, game: NexusGame, update: Update, specific_player: NexusPlayer|None=None):
        if specific_player:
            """Send a game update to all players in a game"""
            print(f"[Server] Sending update to {specific_player.name}")
            # Always send the full state from player's perspective
            #player_index = game.players.index(specific_player)
            #state_data = self.get_player_game_state(game, specific_player)
            #player_update = Update(update.update_type, state_data)
            #message = player_update.to_json()
            message = update.to_json()
            print(f"[Server] Update message: {message}")
            websocket = self.connections.get_socket(specific_player.id)
            await websocket.send(message)
        else:
            """Send a game update to all players in a game"""
            print(f"[Server] Broadcasting update to all players")
            for p in game.players:
                await self.send_game_update(game, update, p)

    async def send_error(self, player: NexusPlayer, error_message: str):
        """Send an error message to a player"""
        print(f"[Server] Sending error to {player.name}: {error_message}")
        update = Update(UpdateType.ERROR, {"message": error_message})
        websocket = self.connections.get_socket(player.id)
        await websocket.send(update.to_json())

    @abstractmethod
    def create_initial_game_state(self, players: List[NexusPlayer]) -> GameState:
        """Create the initial game state - must be implemented by subclass"""
        pass

if __name__ == "__main__":
    server = NexusServer()
    asyncio.run(server.start())

    