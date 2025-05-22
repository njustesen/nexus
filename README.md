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

### Starting the Server
```bash
python .\nexus\network\server.py
```

### Starting the Client
```bash
python ./examples/tictactoe.py --host localhost --port 8765 --create test --password 1234 --name bob
```

```bash
python ./examples/tictactoe.py --host localhost --port 8765 --create test --password 1234 --name alice
```

## License
This project is licensed under the MIT License - see the LICENSE file for details.
