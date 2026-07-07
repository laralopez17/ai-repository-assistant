import numpy as np


def cosine_similarity(left: list[float], right: list[float]) -> float:
    left_vector = np.asarray(left, dtype=float)
    right_vector = np.asarray(right, dtype=float)
    left_norm = np.linalg.norm(left_vector)
    right_norm = np.linalg.norm(right_vector)

    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0

    return float(np.dot(left_vector, right_vector) / (left_norm * right_norm))
