"""The Stop data structure, plus the one bit of geometry everything else needs."""

from __future__ import annotations

import math
from dataclasses import dataclass

from constants import EARTH_RADIUS_M


@dataclass
class Stop:
    stop_id: str
    name: str
    lat: float
    lon: float
    num_members: int = 1  # how many real stops this one represents (1 = not clustered)
    extent_m: float = 0  # how far this one's members actually spread from its center


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))
