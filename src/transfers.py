"""Building walking connections between (dummy) stops."""

from __future__ import annotations

import numpy as np
from constants import EARTH_RADIUS_M
from models import Stop
from sklearn.neighbors import BallTree


def build_walking_transfers(
    stops: dict[str, Stop], max_walk_distance_m: float, walk_speed_mps: float
):
    """All stop pairs within walking distance, as plain
    (from_id, to_id, walk_seconds) tuples.
    """
    stop_ids = list(stops.keys())
    if max_walk_distance_m <= 0 or len(stop_ids) <= 1:
        return []

    coords_rad = np.radians([[stops[sid].lat, stops[sid].lon] for sid in stop_ids])
    tree = BallTree(coords_rad, metric="haversine")
    nearby_idx, nearby_dist = tree.query_radius(
        coords_rad, r=max_walk_distance_m / EARTH_RADIUS_M, return_distance=True
    )

    transfers = []
    for i, (js, dists) in enumerate(zip(nearby_idx, nearby_dist)):
        for j, dist_rad in zip(js, dists):
            if j == i:
                continue
            walk_time_sec = (dist_rad * EARTH_RADIUS_M) / walk_speed_mps
            transfers.append((stop_ids[i], stop_ids[j], walk_time_sec))
    return transfers
