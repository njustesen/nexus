import websocket
import json
import threading
from nexus.game.command import Command
from nexus.game.update import Update

class WebSocketClient:
    def __init__(self, host, port) -> None:
        self.host = host
        self.port = port
        self.ws = None
        self.connected = False
        print(f"[WebSocketClient] Initialized for {host}:{port}")

    def on_message(self, ws, message):
        print(f"[WebSocketClient] Received message: {message}")
        self.last_message = message

    def on_error(self, ws, error):
        print(f"[WebSocketClient] Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("[WebSocketClient] Connection closed")
        self.connected = False

    def on_open(self, ws):
        print("[WebSocketClient] Connection opened")
        self.connected = True

    def connect(self):
        print("[WebSocketClient] Connecting...")
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(
            f"ws://{self.host}:{self.port}",
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        # Run the websocket connection in a separate thread
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        
        # Wait for connection to be established
        while not self.connected:
            pass
        print("[WebSocketClient] Connected successfully")

    def send(self, cmd: Command):
        if not self.connected:
            print("[WebSocketClient] Error: Not connected")
            return
        
        message = cmd.to_json()
        print(f"[WebSocketClient] Sending command: {message}")
        self.ws.send(message)

    def receive(self) -> Update:
        if not hasattr(self, 'last_message'):
            return None
        
        message = self.last_message
        delattr(self, 'last_message')
        
        try:
            data = json.loads(message)
            if "type" in data and data["type"] == "error":
                print(f"[WebSocketClient] Received error: {data['message']}")
                return None
            return Update(**data)
        except json.JSONDecodeError:
            print(f"[WebSocketClient] Error decoding message: {message}")
            return None
        except Exception as e:
            print(f"[WebSocketClient] Error processing message: {str(e)}")
            return None

    def close(self):
        print("[WebSocketClient] Closing connection")
        if self.ws:
            self.ws.close()
            self.ws_thread.join(timeout=1)
        self.connected = False

