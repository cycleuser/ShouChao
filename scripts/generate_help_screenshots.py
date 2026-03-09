#!/usr/bin/env python3
"""Generate CLI help screenshots for ShouChao."""

import os
import subprocess
import sys
from pathlib import Path

PROJ_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = PROJ_DIR / "images"
TOOL_NAME = "shouchao"


def main():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["COLUMNS"] = "80"

    # Generate help text
    result = subprocess.run(
        [sys.executable, "-m", TOOL_NAME, "--help"],
        capture_output=True, text=True, env=env,
    )
    help_text = result.stdout or result.stderr

    # Save text version
    txt_path = IMAGES_DIR / f"{TOOL_NAME}_help.txt"
    txt_path.write_text(help_text, encoding="utf-8")
    print(f"Saved: {txt_path}")

    # Try to generate PNG
    try:
        from PIL import Image, ImageDraw, ImageFont

        bg_color = (30, 30, 30)
        fg_color = (204, 204, 204)
        header_color = (50, 50, 50)
        header_text_color = (180, 180, 180)

        # Find font
        font = None
        for name in ("DejaVuSansMono.ttf", "DejaVuSansMono",
                      "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                      "Consolas", "Courier New"):
            try:
                font = ImageFont.truetype(name, 14)
                break
            except (OSError, IOError):
                continue
        if font is None:
            font = ImageFont.load_default()

        lines = help_text.split("\n")
        line_height = 18
        padding = 15
        header_height = 30
        width = 700
        height = header_height + padding * 2 + len(lines) * line_height + 20

        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        # Header bar
        draw.rectangle([0, 0, width, header_height], fill=header_color)
        draw.text((10, 6), f"$ {TOOL_NAME} --help", fill=header_text_color, font=font)

        # Help text
        y = header_height + padding
        for line in lines:
            draw.text((padding, y), line, fill=fg_color, font=font)
            y += line_height

        png_path = IMAGES_DIR / f"{TOOL_NAME}_help.png"
        img.save(str(png_path))
        print(f"Saved: {png_path}")

    except ImportError:
        print("Pillow not installed, skipping PNG generation")


if __name__ == "__main__":
    main()
