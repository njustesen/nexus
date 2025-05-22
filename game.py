import pygame
from client import WebSocketClient
import sys
from game_state import GameState
from command import Command
from typing import List


class NetworkGame:

    def __init__(self, client: WebSocketClient, game_state: GameState, fps, width, height, title, fullscreen=False) -> None:
        pygame.init()
        self.client = client
        self.fps = fps
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(title)
        if fullscreen:
            self.screen = pygame.display.set_mode((width, height), pygame.FULLSCREEN)
        self.game_state = game_state

    def run(self):
        clock = pygame.time.Clock()
        while True:       
            events = pygame.event.get()  
            for event in events:
                if event.type == pygame.QUIT:
                    self.close()

            # Process game updates from network
            update = self.client.receive()
            if update:
                print("[NetworkGame] Received update:", update.__dict__)
                self.game_state.update(update)
            
            # Process local events and game logic
            self.update(events)
            
            # Draw the game
            self.draw()
            clock.tick(self.fps)

    def send_command(self, command: Command):
        print("[NetworkGame] Sending command:", command.__dict__)
        self.client.send(command)

    def update(self, events: List[pygame.event.EventType]):
        raise NotImplementedError("Subclasses must implement this method")

    def draw(self):
        raise NotImplementedError("Subclasses must implement this method")

    def close(self):
        self.client.close()
        pygame.quit()
        sys.exit()

