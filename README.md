# nexus
A python websocket game server and client framework

## Description
Nexus is a networked tic-tac-toe game with matchmaking capabilities, built using Python and WebSocket technology.

## Prerequisites
- Python 3.7 or higher
- pip (Python package installer)
- Virtual environment tool (optional but recommended)

## Installation

### Option 1: Install from Source (Development)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/nexus.git
   cd nexus
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   # On Windows
   python -m venv venv
   .\venv\Scripts\activate

   # On macOS/Linux
   python -m venv venv
   source venv/bin/activate

   # conda
   conda create --name nexus python=3.11
   conda activate nexus
   ```

3. Install in development mode with all dependencies:
   ```bash
   pip install .
   ```

   or for development:
   ```bash
   pip install -e ".[dev]"
   ```

## Usage

### Installation

Install the package in development mode with test dependencies:
```bash
pip install -e ".[test]"
```

### Running Tests
```bash
# Run all tests
pytest tests/

# Run tests with coverage report
pytest tests/ --cov=nexus

# Run tests verbosely
pytest tests/ -v
```

### Starting the Server
```bash
python examples/tic-tac-toe/tic_tac_toe.py server
```

### Playing the Game

Start the server first:
```bash
python examples/tic-tac-toe/tic_tac_toe.py server
```

Then in separate terminals, players can join in one of three ways:

1. Create a new game as the first player:
```bash
python examples/tic-tac-toe/tic_tac_toe.py client --host localhost --port 8765 --create test --name alice
```

2. Join an existing game as the second player:
```bash
python examples/tic-tac-toe/tic_tac_toe.py client --host localhost --port 8765 --join test --name bob
```

3. Use matchmaking to automatically find an opponent:
```bash
python examples/tic-tac-toe/tic_tac_toe.py client --host localhost --port 8765 --matchmaking --name player1
```

### Command Line Options

Server mode:
```bash
python examples/tic-tac-toe/tic_tac_toe.py server [--port PORT]
```

Client mode:
```bash
python examples/tic-tac-toe/tic_tac_toe.py client [--host HOST] [--port PORT] --name NAME (--create GAME_NAME | --join GAME_NAME | --matchmaking) [--password PASSWORD]
```

Options:
- `--host`: Server hostname (default: localhost)
- `--port`: Server port (default: 8765)
- `--name`: Your player name (required)
- `--create`: Create a new game with the given name
- `--join`: Join an existing game with the given name
- `--matchmaking`: Find a game via matchmaking
- `--password`: Optional password for private games

### Connection Handling

The game handles various connection scenarios:

- If a player disconnects, they can rejoin using the same name
- The game preserves state during disconnections
- Players are notified when their opponent disconnects
- Automatic reconnection attempts occur if connection is lost

## License
This project is licensed under the MIT License - see the LICENSE file for details.