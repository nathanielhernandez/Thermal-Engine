"""
Generate an icon for Thermal Engine.
Creates a simple gauge-style icon.
"""

from PIL import Image, ImageDraw
import os

def create_icon():
    # Create multiple sizes for ICO file
    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw outer ring (cyan)
        padding = size // 8
        draw.ellipse(
            [padding, padding, size - padding, size - padding],
            outline=(0, 200, 255, 255),
            width=max(2, size // 16)
        )

        # Draw inner dark circle
        inner_padding = size // 4
        draw.ellipse(
            [inner_padding, inner_padding, size - inner_padding, size - inner_padding],
            fill=(30, 30, 40, 255)
        )

        # Draw gauge arc (green)
        arc_padding = size // 6
        draw.arc(
            [arc_padding, arc_padding, size - arc_padding, size - arc_padding],
            start=135,
            end=315,
            fill=(0, 255, 150, 255),
            width=max(2, size // 12)
        )

        # Draw center dot
        center = size // 2
        dot_size = max(2, size // 10)
        draw.ellipse(
            [center - dot_size, center - dot_size, center + dot_size, center + dot_size],
            fill=(0, 200, 255, 255)
        )

        images.append(img)

    # Save as ICO
    icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
    images[0].save(
        icon_path,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )
    print(f"Icon created: {icon_path}")

    # Also save as PNG for other uses
    png_path = os.path.join(os.path.dirname(__file__), 'icon.png')
    images[-1].save(png_path, format='PNG')
    print(f"PNG created: {png_path}")

if __name__ == "__main__":
    create_icon()
