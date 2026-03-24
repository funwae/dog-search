"""Perceptual hash-based image embeddings.

Uses average-hash (aHash) and difference-hash (dHash) from Pillow.
These are lightweight, require no ML model, and are surprisingly
effective for near-duplicate detection and coarse visual similarity.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

HASH_SIZE = 16  # 16x16 = 256-bit hash


def average_hash(img: Image.Image, size: int = HASH_SIZE) -> int:
    """Compute average hash: resize, grayscale, threshold at mean."""
    img = img.resize((size, size), Image.Resampling.LANCZOS).convert("L")
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = 0
    for px in pixels:
        bits = (bits << 1) | (1 if px >= avg else 0)
    return bits


def difference_hash(img: Image.Image, size: int = HASH_SIZE) -> int:
    """Compute difference hash: resize to (size+1, size), compare adjacent pixels."""
    img = img.resize((size + 1, size), Image.Resampling.LANCZOS).convert("L")
    pixels = list(img.getdata())
    bits = 0
    for row in range(size):
        for col in range(size):
            idx = row * (size + 1) + col
            bits = (bits << 1) | (1 if pixels[idx] > pixels[idx + 1] else 0)
    return bits


def color_histogram(img: Image.Image, bins: int = 8) -> list[float]:
    """Compute normalized color histogram (R, G, B channels)."""
    img = img.resize((64, 64), Image.Resampling.LANCZOS).convert("RGB")
    hist: list[float] = []
    for channel in range(3):
        channel_data = [img.getpixel((x, y))[channel] for y in range(64) for x in range(64)]
        bin_width = 256 / bins
        bin_counts = [0.0] * bins
        for val in channel_data:
            b = min(int(val / bin_width), bins - 1)
            bin_counts[b] += 1.0
        total = sum(bin_counts)
        hist.extend(c / total for c in bin_counts)
    return hist


class ImageEmbedding:
    """A perceptual embedding for one image region."""

    __slots__ = ("ahash", "dhash", "color_hist", "label")

    def __init__(self, ahash: int, dhash: int, color_hist: list[float], label: str = "whole"):
        self.ahash = ahash
        self.dhash = dhash
        self.color_hist = color_hist
        self.label = label

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "ahash": hex(self.ahash),
            "dhash": hex(self.dhash),
            "color_hist": [round(v, 4) for v in self.color_hist],
        }

    @classmethod
    def from_image(cls, img: Image.Image, label: str = "whole") -> "ImageEmbedding":
        return cls(
            ahash=average_hash(img),
            dhash=difference_hash(img),
            color_hist=color_histogram(img),
            label=label,
        )


def embed_image(path: str | Path) -> list[ImageEmbedding]:
    """Generate embeddings for whole image plus crops."""
    from .detector import get_dog_crops

    crops = get_dog_crops(path)
    return [ImageEmbedding.from_image(img, label) for label, img in crops.items()]
