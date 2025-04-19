import numpy as np


# do not change the code in the block below
# __________start of block__________
class DummyMatch:
    def __init__(self, queryIdx, trainIdx, distance):
        self.queryIdx = queryIdx  # index in des1
        self.trainIdx = trainIdx  # index in des2
        self.distance = distance
# __________end of block__________


def match_key_points_numpy(des1: np.ndarray, des2: np.ndarray) -> list:
    """
    Match descriptors using brute-force matching with cross-check.

    Args:
        des1 (np.ndarray): Descriptors from image 1, shape (N1, D)
        des2 (np.ndarray): Descriptors from image 2, shape (N2, D)

    Returns:
        List[DummyMatch]: Sorted list of mutual best matches.
    """
    matches = []
    
    if des1 is None or des2 is None or len(des1) == 0 or len(des2) == 0:
        return matches

    dists = np.sqrt(((des1[:, np.newaxis, :] - des2[np.newaxis, :, :]) ** 2).sum(axis=2))

    
    # Find the nearest neighbor for each descriptor in des1
    best_match_idx_1 = np.argmin(dists, axis=1)
    best_match_dist_1 = np.min(dists, axis=1)

    # Find the nearest neighbor for each descriptor in des2
    best_match_idx_2 = np.argmin(dists, axis=0)
    best_match_dist_2 = np.min(dists, axis=0)    
    
    # Perform cross-checking
    for i, idx_2 in enumerate(best_match_idx_1):
        if idx_2 < len(best_match_idx_2) and best_match_idx_2[idx_2] == i:
            matches.append(DummyMatch(i, idx_2, best_match_dist_1[i]))

    # Sort the matches by distance
    matches.sort(key=lambda x: x.distance)
    
    return matches