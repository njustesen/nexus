import websocket
import json
import threading
from queue import Queue
from nexus.network.command import Command, CommandType
from nexus.network.update import Update

class NexusClient:
    """Base client class for the Nexus framework"""
    def __init__(self, host, port) -> None:
        self.host = host
        self.port = port
        self.ws = None
        self.connected = False
        self.message_queue = Queue()
        # Store info needed for reconnection
        self.current_game = None
        self.player_name = None
        self.game_password = None
        print(f"[NexusClient] Initialized for {host}:{port}")

    def on_message(self, ws, message):
        print(f"[NexusClient] Received message: {message}")
        self.message_queue.put(message)

    def on_error(self, ws, error):
        print(f"[NexusClient] Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"[NexusClient] Connection closed (status: {close_status_code}, msg: {close_msg})")
        self.connected = False
        # Clean up the WebSocket object
        self.ws = None
        # Notify any listeners that we've disconnected
        print("[NexusClient] Connection to server lost - attempting to reconnect...")
        # Try to reconnect if we were in a game
        if self.current_game and self.player_name:
            self.reconnect()

    def on_open(self, ws):
        print("[NexusClient] Connection opened")
        self.connected = True
        # If we were in a game, rejoin it
        if self.current_game and self.player_name:
            print(f"[NexusClient] Attempting to rejoin game: {self.current_game}")
            self.send(Command(CommandType.JOIN_GAME, {
                "game_name": self.current_game,
                "player_name": self.player_name,
                "password": self.game_password
            }))

    def on_ping(self, ws, message):
        """Called when server sends a ping"""
        print("[NexusClient] Received ping from server")

    def on_pong(self, ws, message):
        """Called when server responds to our ping"""
        print("[NexusClient] Received pong from server")

    def connect(self):
        print("[NexusClient] Connecting...")
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(
            f"ws://{self.host}:{self.port}",
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open,
            on_ping=self.on_ping,
            on_pong=self.on_pong
        )
        
        # Run the websocket connection in a separate thread
        self.ws_thread = threading.Thread(
            target=lambda: self.ws.run_forever(
                ping_interval=30,  # Check connection every 30 seconds
                ping_timeout=10    # Wait 10 seconds for pong response
            )
        )
        self.ws_thread.daemon = True
        self.ws_thread.start()
        
        # Wait for connection to be established
        while not self.connected:
            pass
        print("[NexusClient] Connected successfully")

    def reconnect(self):
        """Try to reconnect to the server"""
        import time
        retry_delay = 5  # Start with 5 second delay
        max_delay = 30   # Maximum delay between retries
        
        while not self.connected:
            print(f"[NexusClient] Attempting to reconnect in {retry_delay} seconds...")
            time.sleep(retry_delay)
            try:
                self.connect()
                if self.connected:
                    print("[NexusClient] Reconnection successful")
                    return
            except Exception as e:
                print(f"[NexusClient] Reconnection failed: {str(e)}")
                # Increase delay for next attempt, but don't exceed max_delay
                retry_delay = min(retry_delay * 2, max_delay)

    def send(self, cmd: Command):
        if not self.connected:
            print("[NexusClient] Error: Not connected")
            return
        
        message = cmd.to_json()
        print(f"[NexusClient] Sending command: {message}")
        
        # Store game info when joining or creating a game
        if cmd.command_type in [CommandType.CREATE_GAME, CommandType.JOIN_GAME]:
            self.current_game = cmd.data.get("game_name")
            self.player_name = cmd.data.get("player_name")
            self.game_password = cmd.data.get("password")
        elif cmd.command_type == CommandType.FIND_GAME:
            self.player_name = cmd.data.get("player_name")
            # Note: game name will be set when we receive the game assignment
        
        self.ws.send(message)

    def receive(self) -> Update:
        if self.message_queue.empty():
            return None
            
        try:
            message = self.message_queue.get_nowait()
            data = json.loads(message)
            if "type" in data and data["type"] == "error":
                print(f"[NexusClient] Received error: {data['message']}")
                return None
                
            # If this is a game assignment from matchmaking, store the game name
            if "type" in data and data["type"] == "game_assignment":
                self.current_game = data.get("game_name")
                
            return Update(**data)
        except json.JSONDecodeError:
            print(f"[NexusClient] Error decoding message: {message}")
            return None
        except Exception as e:
            print(f"[NexusClient] Error processing message: {str(e)}")
            return None

    def close(self):
        print("[NexusClient] Closing connection")
        if self.ws and self.connected:
            try:
                # Send disconnect command
                self.send(Command(CommandType.DISCONNECT, {}))
                # Clear game info
                self.current_game = None
                self.player_name = None
                self.game_password = None
                # Close the connection
                self.ws.close()
                self.ws_thread.join(timeout=1)
            except Exception as e:
                print(f"[NexusClient] Error during close: {str(e)}")
            finally:
                self.connected = False
                self.ws = None

