import sys
from nexus.network.update import UpdateType
import pygame
from typing import List, TypeVar, Generic, Type, get_args
from nexus.network.player import NexusPlayer
from nexus.network.client import NexusClient
from nexus.game.gamestate import GameState, GamePhase
from nexus.network.command import Command


T = TypeVar('T', bound=GameState)

class NexusGame(Generic[T]):
    """Base game class for the Nexus framework"""

    def __init__(self, client: NexusClient, game_state: T|None, fps: int, width: int, height: int, title: str, fullscreen: bool = False) -> None:
        pygame.init()
        self.client = client
        self.fps = fps
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(title)
        if fullscreen:
            self.screen = pygame.display.set_mode((width, height), pygame.FULLSCREEN)
        self.game_state = game_state
        self.state_class = self._get_state_class()

    @classmethod
    def _get_state_class(cls) -> Type[T]:
        """Extract the concrete GameState class from the generic type parameter."""
        for base in cls.__orig_bases__:
            if hasattr(base, "__origin__") and base.__origin__ is NexusGame:
                return base.__args__[0]
        raise TypeError("NexusGame requires a concrete GameState type parameter")

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
                print("[NexusGame] Received update:", update.__dict__)
                print("[NexusGame] Processing update type:", update.update_type)
                if update.update_type == UpdateType.GAME_STARTED:
                    # Use the actual state class for deserialization
                    self.game_state = self.state_class.from_dict(update.data)
                elif self.game_state is None:
                    print("[NexusGame] Game state is not set, skipping update")
                elif update.update_type == UpdateType.GAME_STATE_UPDATE:
                    print("[NexusGame] Applying game state update:", update.data)
                    print("[NexusGame] Current game state before update:", self.game_state)
                    self.game_state.apply(update)
                    print("[NexusGame] Current game state after update:", self.game_state)
                elif update.update_type == UpdateType.GAME_OVER:
                    self.game_state.winner = update.data["winner"]
                    self.game_state.game_over = True
                    self.game_state.phase = GamePhase.END_GAME
                elif update.update_type == UpdateType.ERROR:
                    print("[NexusGame] Error:", update.data["message"])
                else:
                    print("[NexusGame] Unknown update type:", update.update_type)
            
            # Process local events and game logic
            self.update(events)
            
            # Draw the game
            self.draw()
            clock.tick(self.fps)

    def send_command(self, command: Command):
        print("[NexusGame] Sending command:", command.__dict__)
        self.client.send(command)

    def update(self, events: List[pygame.event.EventType]):
        raise NotImplementedError("Subclasses must implement this method")

    def draw(self):
        raise NotImplementedError("Subclasses must implement this method")

    def close(self):
        self.client.close()
        pygame.quit()
        sys.exit()

