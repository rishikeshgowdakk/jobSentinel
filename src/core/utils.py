import math

def calculate_cosine_similarity(v1, v2):
    """Calculate cosine similarity between two vectors."""
    if not v1 or not v2:
        return 0.0
    dot_product = sum(x * y for x, y in zip(v1, v2))
    magnitude1 = math.sqrt(sum(x * x for x in v1))
    magnitude2 = math.sqrt(sum(x * x for x in v2))
    if not magnitude1 or not magnitude2:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)
