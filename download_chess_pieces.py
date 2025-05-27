import os
import requests
import glob

def download_piece(piece_name, color):
    url = f"https://lichess1.org/assets/piece/cburnett/{color}{piece_name}.svg"
    output_dir = "assets/chess"
    os.makedirs(output_dir, exist_ok=True)
    
    response = requests.get(url)
    if response.status_code == 200:
        with open(f"{output_dir}/{color}_{piece_name.lower()}.svg", "wb") as f:
            f.write(response.content)
        print(f"Downloaded {color}_{piece_name.lower()}.svg")
    else:
        print(f"Failed to download {color}_{piece_name.lower()}.svg")

# Create pieces
pieces = ["K", "Q", "R", "B", "N", "P"]  # King, Queen, Rook, Bishop, Knight, Pawn
colors = ["w", "b"]  # white, black

# First, clean up any existing files
for f in glob.glob("assets/chess/*.png") + glob.glob("assets/chess/*.svg"):
    try:
        os.remove(f)
        print(f"Removed old file: {f}")
    except:
        pass

# Download all pieces
for color in colors:
    for piece in pieces:
        download_piece(piece, color)

print("Chess pieces downloaded successfully!") 