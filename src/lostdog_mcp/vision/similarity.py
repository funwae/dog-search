"""Image similarity scoring using perceptual hashes and color histograms."""

from __future__ import annotations

from math import sqrt

from .embedder import ImageEmbedding, HASH_SIZE


def hamming_distance(a: int, b: int) -> int:
    """Count differing bits between two integers."""
    return bin(a ^ b).count("1")


def hash_similarity(a: int, b: int, total_bits: int = HASH_SIZE * HASH_SIZE) -> float:
    """Convert hamming distance to a 0-1 similarity score."""
    dist = hamming_distance(a, b)
    return max(0.0, 1.0 - (dist / total_bits))


def histogram_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two histogram vectors."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sqrt(sum(x * x for x in a))
    mag_b = sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def embedding_similarity(a: ImageEmbedding, b: ImageEmbedding) -> float:
    """Combined similarity between two embeddings of the same region type.

    Weights: aHash=0.30, dHash=0.35, color=0.35
    """
    ahash_sim = hash_similarity(a.ahash, b.ahash)
    dhash_sim = hash_similarity(a.dhash, b.dhash)
    color_sim = histogram_similarity(a.color_hist, b.color_hist)
    return 0.30 * ahash_sim + 0.35 * dhash_sim + 0.35 * color_sim


def compare_image_sets(
    case_embeddings: list[ImageEmbedding],
    candidate_embeddings: list[ImageEmbedding],
) -> float:
    """Compare two sets of embeddings, matching by label.

    Returns the best average similarity across matching region labels.
    Falls back to whole-image comparison if labels don't match.
    """
    if not case_embeddings or not candidate_embeddings:
        return 0.0

    case_by_label = {e.label: e for e in case_embeddings}
    cand_by_label = {e.label: e for e in candidate_embeddings}

    scores: list[float] = []
    for label in ("whole", "body", "head"):
        if label in case_by_label and label in cand_by_label:
            scores.append(embedding_similarity(case_by_label[label], cand_by_label[label]))

    if not scores:
        # Fallback: compare first embedding from each set
        return embedding_similarity(case_embeddings[0], candidate_embeddings[0])

    # Weight: whole=0.3, body=0.45, head=0.25
    weights = {"whole": 0.3, "body": 0.45, "head": 0.25}
    label_list = [label for label in ("whole", "body", "head") if label in case_by_label and label in cand_by_label]
    total_weight = sum(weights.get(l, 0.3) for l in label_list)
    weighted = sum(
        weights.get(l, 0.3) * embedding_similarity(case_by_label[l], cand_by_label[l])
        for l in label_list
    )
    return weighted / total_weight if total_weight > 0 else 0.0
