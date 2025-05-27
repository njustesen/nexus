from PIL import Image, ImageDraw
import os

def draw_pawn(draw, color, width, height):
    # Base
    draw.ellipse([width*0.35, height*0.8, width*0.65, height*0.95], fill=color)
    # Body
    draw.ellipse([width*0.4, height*0.5, width*0.6, height*0.7], fill=color)
    # Head
    draw.ellipse([width*0.35, height*0.25, width*0.65, height*0.45], fill=color)

def draw_rook(draw, color, width, height):
    # Base
    draw.rectangle([width*0.3, height*0.8, width*0.7, height*0.95], fill=color)
    # Body
    draw.rectangle([width*0.35, height*0.4, width*0.65, height*0.8], fill=color)
    # Top
    draw.rectangle([width*0.25, height*0.25, width*0.75, height*0.4], fill=color)
    # Battlements
    for x in [0.25, 0.42, 0.58]:
        draw.rectangle([width*x, height*0.15, width*(x+0.17), height*0.25], fill=color)

def draw_knight(draw, color, width, height):
    # Base
    draw.ellipse([width*0.35, height*0.8, width*0.65, height*0.95], fill=color)
    # Body
    points = [
        (width*0.4, height*0.8),
        (width*0.4, height*0.4),
        (width*0.3, height*0.3),
        (width*0.35, height*0.2),
        (width*0.5, height*0.15),
        (width*0.7, height*0.3),
        (width*0.6, height*0.8),
    ]
    draw.polygon(points, fill=color)
    # Eye
    if color == (0, 0, 0):
        eye_color = (255, 255, 255)
    else:
        eye_color = (0, 0, 0)
    draw.ellipse([width*0.45, height*0.25, width*0.5, height*0.3], fill=eye_color)

def draw_bishop(draw, color, width, height):
    # Base
    draw.ellipse([width*0.35, height*0.8, width*0.65, height*0.95], fill=color)
    # Body
    points = [
        (width*0.4, height*0.8),
        (width*0.35, height*0.4),
        (width*0.5, height*0.2),
        (width*0.65, height*0.4),
        (width*0.6, height*0.8),
    ]
    draw.polygon(points, fill=color)
    # Head
    draw.ellipse([width*0.45, height*0.1, width*0.55, height*0.2], fill=color)

def draw_queen(draw, color, width, height):
    # Base
    draw.ellipse([width*0.35, height*0.8, width*0.65, height*0.95], fill=color)
    # Body
    points = [
        (width*0.4, height*0.8),
        (width*0.3, height*0.4),
        (width*0.5, height*0.2),
        (width*0.7, height*0.4),
        (width*0.6, height*0.8),
    ]
    draw.polygon(points, fill=color)
    # Crown points
    for x in [0.3, 0.4, 0.5, 0.6, 0.7]:
        draw.ellipse([width*x-5, height*0.1, width*x+5, height*0.2], fill=color)

def draw_king(draw, color, width, height):
    # Base
    draw.ellipse([width*0.35, height*0.8, width*0.65, height*0.95], fill=color)
    # Body
    points = [
        (width*0.4, height*0.8),
        (width*0.3, height*0.4),
        (width*0.5, height*0.25),
        (width*0.7, height*0.4),
        (width*0.6, height*0.8),
    ]
    draw.polygon(points, fill=color)
    # Cross
    draw.rectangle([width*0.45, height*0.05, width*0.55, height*0.25], fill=color)
    draw.rectangle([width*0.35, height*0.12, width*0.65, height*0.18], fill=color)

def create_piece(name, color):
    # Create a new image with transparency
    size = 100
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Set colors
    piece_color = (255, 255, 255) if color == "white" else (0, 0, 0)
    
    # Draw the appropriate piece
    if name == "pawn":
        draw_pawn(draw, piece_color, size, size)
    elif name == "rook":
        draw_rook(draw, piece_color, size, size)
    elif name == "knight":
        draw_knight(draw, piece_color, size, size)
    elif name == "bishop":
        draw_bishop(draw, piece_color, size, size)
    elif name == "queen":
        draw_queen(draw, piece_color, size, size)
    elif name == "king":
        draw_king(draw, piece_color, size, size)
    
    # Save the image
    os.makedirs("assets/chess", exist_ok=True)
    img.save(f"assets/chess/{color}_{name}.png")

# Create all pieces
pieces = ["king", "queen", "rook", "bishop", "knight", "pawn"]

# Generate both white and black pieces
for name in pieces:
    create_piece(name, "white")
    create_piece(name, "black")

print("Chess pieces generated successfully!") 