"""Tests for vision pipeline: hashing, embedding, similarity."""

from __future__ import annotations

from PIL import Image

from lostdog_mcp.vision.embedder import (
    ImageEmbedding,
    average_hash,
    color_histogram,
    difference_hash,
)
from lostdog_mcp.vision.similarity import (
    compare_image_sets,
    embedding_similarity,
    hamming_distance,
    hash_similarity,
    histogram_similarity,
)
from lostdog_mcp.vision.detector import center_crop, top_center_crop


def _red_image(size=(100, 100)) -> Image.Image:
    """Create an image with red gradient (has pixel variance for hashing)."""
    img = Image.new("RGB", size)
    for y in range(size[1]):
        for x in range(size[0]):
            img.putpixel((x, y), (255, int(y * 255 / size[1]), int(x * 50 / size[0])))
    return img


def _blue_image(size=(100, 100)) -> Image.Image:
    """Create an image with blue gradient."""
    img = Image.new("RGB", size)
    for y in range(size[1]):
        for x in range(size[0]):
            img.putpixel((x, y), (int(x * 50 / size[0]), int(y * 50 / size[1]), 255))
    return img


def _similar_red_image(size=(100, 100)) -> Image.Image:
    """Create an image similar to _red_image but slightly shifted."""
    img = Image.new("RGB", size)
    for y in range(size[1]):
        for x in range(size[0]):
            img.putpixel((x, y), (250, int(y * 250 / size[1]), int(x * 55 / size[0])))
    return img


# ── Hash tests ───────────────────────────────────────────────────────────

def test_average_hash_identical_images():
    img = _red_image()
    h1 = average_hash(img)
    h2 = average_hash(img)
    assert h1 == h2


def test_average_hash_different_images():
    h1 = average_hash(_red_image())
    h2 = average_hash(_blue_image())
    # Different images should have different hashes
    assert h1 != h2


def test_difference_hash_identical():
    img = _red_image()
    assert difference_hash(img) == difference_hash(img)


def test_hamming_distance_identical():
    assert hamming_distance(0b1010, 0b1010) == 0


def test_hamming_distance_all_different():
    assert hamming_distance(0b1111, 0b0000) == 4


def test_hash_similarity_identical():
    h = average_hash(_red_image())
    assert hash_similarity(h, h) == 1.0


def test_hash_similarity_very_different():
    h1 = average_hash(_red_image())
    h2 = average_hash(_blue_image())
    sim = hash_similarity(h1, h2)
    assert sim < 0.9  # Should be different


# ── Color histogram tests ────────────────────────────────────────────────

def test_color_histogram_length():
    hist = color_histogram(_red_image(), bins=8)
    assert len(hist) == 24  # 3 channels * 8 bins


def test_histogram_similarity_identical():
    h = color_histogram(_red_image())
    assert histogram_similarity(h, h) > 0.99


def test_histogram_similarity_different():
    h1 = color_histogram(_red_image())
    h2 = color_histogram(_blue_image())
    sim = histogram_similarity(h1, h2)
    assert sim < 0.5  # Very different colors


# ── Embedding tests ──────────────────────────────────────────────────────

def test_embedding_from_image():
    emb = ImageEmbedding.from_image(_red_image(), "whole")
    assert emb.label == "whole"
    assert isinstance(emb.ahash, int)
    assert isinstance(emb.dhash, int)
    assert len(emb.color_hist) == 24


def test_embedding_to_dict():
    emb = ImageEmbedding.from_image(_red_image(), "body")
    d = emb.to_dict()
    assert d["label"] == "body"
    assert "ahash" in d
    assert "dhash" in d


def test_embedding_similarity_identical():
    emb = ImageEmbedding.from_image(_red_image())
    sim = embedding_similarity(emb, emb)
    assert sim > 0.95


def test_embedding_similarity_different():
    e1 = ImageEmbedding.from_image(_red_image())
    e2 = ImageEmbedding.from_image(_blue_image())
    sim = embedding_similarity(e1, e2)
    assert sim < 0.8


def test_embedding_similarity_similar():
    e1 = ImageEmbedding.from_image(_red_image())
    e2 = ImageEmbedding.from_image(_similar_red_image())
    sim = embedding_similarity(e1, e2)
    assert sim > 0.9  # Very similar images


# ── Image set comparison ─────────────────────────────────────────────────

def test_compare_image_sets_identical():
    embs = [ImageEmbedding.from_image(_red_image(), label) for label in ("whole", "body", "head")]
    sim = compare_image_sets(embs, embs)
    assert sim > 0.95


def test_compare_image_sets_different():
    case_embs = [ImageEmbedding.from_image(_red_image(), "whole")]
    cand_embs = [ImageEmbedding.from_image(_blue_image(), "whole")]
    sim = compare_image_sets(case_embs, cand_embs)
    assert sim < 0.8


def test_compare_image_sets_empty():
    assert compare_image_sets([], []) == 0.0


# ── Detector tests ───────────────────────────────────────────────────────

def test_center_crop_reduces_size():
    img = _red_image((200, 200))
    cropped = center_crop(img, 0.5)
    assert cropped.size == (100, 100)


def test_top_center_crop():
    img = _red_image((200, 200))
    cropped = top_center_crop(img, 0.4)
    assert cropped.size[0] == 80
    assert cropped.size[1] == 80
