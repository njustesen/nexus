import websocket
import json
import threading
from queue import Queue
from nexus.network.command import Command
from nexus.network.update import Update

class NexusClient:
    """Base client class for the Nexus framework"""
    def __init__(self, host, port) -> None:
        self.host = host
        self.port = port
        self.ws = None
        self.connected = False
        self.message_queue = Queue()
        print(f"[NexusClient] Initialized for {host}:{port}")

    def on_message(self, ws, message):
        print(f"[NexusClient] Received message: {message}")
        self.message_queue.put(message)

    def on_error(self, ws, error):
        print(f"[NexusClient] Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("[NexusClient] Connection closed")
        self.connected = False

    def on_open(self, ws):
        print("[NexusClient] Connection opened")
        self.connected = True

    def connect(self):
        print("[NexusClient] Connecting...")
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
        print("[NexusClient] Connected successfully")

    def send(self, cmd: Command):
        if not self.connected:
            print("[NexusClient] Error: Not connected")
            return
        
        message = cmd.to_json()
        print(f"[NexusClient] Sending command: {message}")
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
            return Update(**data)
        except json.JSONDecodeError:
            print(f"[NexusClient] Error decoding message: {message}")
            return None
        except Exception as e:
            print(f"[NexusClient] Error processing message: {str(e)}")
            return None

    def close(self):
        print("[NexusClient] Closing connection")
        if self.ws:
            self.ws.close()
            self.ws_thread.join(timeout=1)
        self.connected = False

