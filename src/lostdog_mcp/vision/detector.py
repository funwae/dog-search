"""Dog region detection and cropping.

Phase 2 uses simple center-crop heuristic. A real detector (YOLO, etc.)
can be swapped in later without changing the interface.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def load_image(path: str | Path) -> Image.Image:
    """Load an image from disk, convert to RGB."""
    return Image.open(path).convert("RGB")


def center_crop(img: Image.Image, ratio: float = 0.6) -> Image.Image:
    """Crop the center region of an image (heuristic dog crop)."""
    w, h = img.size
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    left = (w - new_w) // 2
    top = (h - new_h) // 2
    return img.crop((left, top, left + new_w, top + new_h))


def top_center_crop(img: Image.Image, ratio: float = 0.4) -> Image.Image:
    """Crop the top-center region (heuristic head crop)."""
    w, h = img.size
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    left = (w - new_w) // 2
    top = int(h * 0.05)
    return img.crop((left, top, left + new_w, top + new_h))


def get_dog_crops(path: str | Path) -> dict[str, Image.Image]:
    """Return whole image, body crop, and head crop.

    Keys: 'whole', 'body', 'head'
    """
    img = load_image(path)
    return {
        "whole": img,
        "body": center_crop(img, 0.6),
        "head": top_center_crop(img, 0.4),
    }
