"""Clustering nearby stops into dummy stops."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from constants import EARTH_RADIUS_M, PAIDE_STOP_IDS, TURI_STOP_IDS
from models import Stop, haversine_m
from sklearn.neighbors import BallTree


def _cluster_by_distance(
    stops: dict[str, Stop], radius_m: float, pre_claimed: set[str] = frozenset()
) -> dict[str, str]:
    """Group stops within radius_m of each other. Simple greedy method:
    go through stops one at a time; if a stop isn't in a cluster yet,
    claim every not-yet-claimed stop within radius_m of it, and name the
    new cluster after this first ("seed") stop. With radius_m = 0, every
    stop stays in its own singleton cluster — nothing changes.

    pre_claimed stops are skipped entirely — never used as a seed, never
    claimed as someone else's neighbor. That's how build_clusters keeps
    Paide/Türi stops out of the general clustering altogether, instead of
    just overriding their result afterward (which would leave behind
    whatever they'd already claimed as a seed).
    """
    stop_ids = list(stops.keys())
    cluster_of = {sid: sid for sid in stop_ids}
    if radius_m <= 0:
        return cluster_of

    coords_rad = np.radians([[stops[sid].lat, stops[sid].lon] for sid in stop_ids])
    tree = BallTree(coords_rad, metric="haversine")
    nearby = tree.query_radius(coords_rad, r=radius_m / EARTH_RADIUS_M)

    claimed = set(pre_claimed)
    for i, sid in enumerate(stop_ids):
        if sid in claimed:
            continue
        for j in nearby[i]:
            neighbor_id = stop_ids[j]
            if neighbor_id not in claimed:
                cluster_of[neighbor_id] = sid
                claimed.add(neighbor_id)
    return cluster_of


def build_clusters(stops: dict[str, Stop], radius_m: float) -> dict[str, str]:
    """The general distance-based clustering, plus the fixed Paide/Türi
    override on top — those two towns are always their own dummy stop,
    regardless of radius_m.
    """
    forced = PAIDE_STOP_IDS | TURI_STOP_IDS
    cluster_of = _cluster_by_distance(stops, radius_m, pre_claimed=forced)
    for sid in PAIDE_STOP_IDS:
        cluster_of[sid] = "PAIDE"
    for sid in TURI_STOP_IDS:
        cluster_of[sid] = "TURI"
    return cluster_of


def build_dummy_stops(
    stops: dict[str, Stop], cluster_of: dict[str, str], radius_m: float
) -> dict[str, Stop]:
    """One Stop per cluster.

    General clusters (found by _cluster_by_distance) are placed at their
    seed stop's own position, with a coverage circle of exactly radius_m —
    that's guaranteed to contain every member, since that's exactly how
    _cluster_by_distance found them (everyone within radius_m of the
    seed). So every general cluster's circle is the same size, by
    construction.

    PAIDE/TURI are different: a fixed, hand-picked set of real stops, not
    found by radius at all, so they can be spread out unevenly. They get
    their true center (average position) and true footprint (max
    distance from that center to any member) instead.
    """
    members_by_cluster = defaultdict(list)
    for stop_id, cluster_id in cluster_of.items():
        members_by_cluster[cluster_id].append(stop_id)

    dummy_stops = {}
    for cluster_id, member_ids in members_by_cluster.items():
        if cluster_id in ("PAIDE", "TURI"):
            lat = sum(stops[m].lat for m in member_ids) / len(member_ids)
            lon = sum(stops[m].lon for m in member_ids) / len(member_ids)
            extent_m = max(
                haversine_m(lat, lon, stops[m].lat, stops[m].lon) for m in member_ids
            )
            name = "Paide" if cluster_id == "PAIDE" else "Türi"
        else:
            lat, lon = stops[cluster_id].lat, stops[cluster_id].lon
            extent_m = radius_m
            name = (
                stops[cluster_id].name
                if len(member_ids) == 1
                else f"{stops[cluster_id].name} ümbrus ({len(member_ids)} peatust)"
            )

        dummy_stops[cluster_id] = Stop(
            cluster_id, name, lat, lon, num_members=len(member_ids), extent_m=extent_m
        )
    return dummy_stops
