"""Drawing the map."""

from __future__ import annotations

import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from constants import EARTH_RADIUS_M
from models import Stop


def hhmm_to_seconds(hhmm: str | None) -> int | None:
    """ "H:MM" or "HH:MM" -> seconds since midnight. None stays None."""
    if hhmm is None:
        return None
    h, m = hhmm.split(":")
    return int(h) * 3600 + int(m) * 60


def seconds_to_hhmm(seconds) -> str:
    seconds = int(seconds)
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    h, rem = divmod(seconds, 3600)
    m, _ = divmod(rem, 60)
    return f"{sign}{h:02d}:{m:02d}"


def reach_to_dataframe(
    reach: dict[str, int], dummy_stops: dict[str, Stop]
) -> pd.DataFrame:
    rows = [
        {
            "stop_id": stop_id,
            "name": dummy_stops[stop_id].name,
            "lat": dummy_stops[stop_id].lat,
            "lon": dummy_stops[stop_id].lon,
            "latest_departure_sec": latest_sec,
            "latest_departure_hours": latest_sec / 3600,
            "latest_departure": seconds_to_hhmm(latest_sec),
            "extent_m": dummy_stops[stop_id].extent_m,
        }
        for stop_id, latest_sec in reach.items()
        if stop_id in dummy_stops
    ]
    columns = [
        "stop_id", "name", "lat", "lon",
        "latest_departure_sec", "latest_departure_hours", "latest_departure",
        "extent_m",
    ]
    df = pd.DataFrame(rows, columns=columns)  # keeps these columns even if rows is empty
    numeric_columns = ["lat", "lon", "latest_departure_sec", "latest_departure_hours", "extent_m"]
    df[numeric_columns] = df[numeric_columns].astype(float)  # empty rows default to object dtype otherwise
    return df.sort_values("latest_departure_sec", ascending=False).reset_index(
        drop=True
    )


def _circle_points(lat: float, lon: float, radius_m: float, n_points: int = 32):
    """Points tracing a circle of radius_m meters around (lat, lon), using
    a flat-earth approximation — fine at the few-km scale these circles
    are drawn at.
    """
    lats, lons = [], []
    for i in range(n_points + 1):  # +1 to close the loop back on itself
        theta = 2 * math.pi * i / n_points
        dlat = (radius_m * math.cos(theta)) / EARTH_RADIUS_M * (180 / math.pi)
        dlon = (
            (radius_m * math.sin(theta))
            / (EARTH_RADIUS_M * math.cos(math.radians(lat)))
            * (180 / math.pi)
        )
        lats.append(lat + dlat)
        lons.append(lon + dlon)
    return lats, lons


def _coverage_circles_trace(df: pd.DataFrame):
    """One trace drawing every cluster's real coverage area — a circle of
    radius extent_m around its center. Each circle is separated by a
    `None` so they fill independently instead of merging into one blob.
    Clusters with extent_m = 0 (singleton stops) draw nothing.
    """
    all_lats: list = []
    all_lons: list = []
    for lat, lon, extent_m in zip(df["lat"], df["lon"], df["extent_m"]):
        if extent_m <= 0:
            continue
        circle_lats, circle_lons = _circle_points(lat, lon, extent_m)
        all_lats.extend([*circle_lats, None])
        all_lons.extend([*circle_lons, None])

    return go.Scattermap(
        lat=all_lats,
        lon=all_lons,
        mode="lines",
        fill="toself",
        fillcolor="rgba(70, 130, 180, 0.15)",
        line=dict(color="rgba(70, 130, 180, 0.6)", width=1),
        hoverinfo="skip",
        showlegend=False,
    )


def build_map(
    df: pd.DataFrame,
    color_range: tuple[float, float] | None = None,
    center: dict | None = None,
):
    """color_range and center let callers pin the color scale and map
    framing to fixed values — e.g. an animation across many frames should
    use the same scale/framing throughout, not let each frame re-derive
    it from just its own (shrinking) set of points.
    """
    df = df.copy()
    df["coordinates"] = (
        df["lat"].round(5).astype(str) + ", " + df["lon"].round(5).astype(str)
    )

    fig = px.scatter_map(
        df,
        lat="lat",
        lon="lon",
        color="latest_departure_hours",
        hover_name="name",
        hover_data={
            "latest_departure": True,
            "latest_departure_hours": False,
            "extent_m": ":.0f",
            "coordinates": True,
            "lat": False,
            "lon": False,
        },
        # English column names above, renamed to Estonian for display here.
        labels={
            "extent_m": "raadius (m)",
            "latest_departure": "Viimane väljumisaeg",
            "coordinates": "Koordinaadid",
        },
        color_continuous_scale="Viridis",
        range_color=color_range,
        center=center,
        zoom=6,
        height=700,
        title="Hiliseim väljumine, et jõuda Paidesse/Türisse valitud kellaajaks.",
    )
    fig.update_traces(marker=dict(size=6))  # small, fixed — just marks each center

    # Underneath the dots, draw each cluster's actual coverage circle, so
    # the map shows the real geographic area that got merged into each
    # dot, not just a bigger dot standing in for "there's an area here".
    fig.add_trace(_coverage_circles_trace(df))
    fig.data = (fig.data[-1], *fig.data[:-1])  # circles first = drawn on the bottom

    range_min, range_max = color_range or (
        df["latest_departure_hours"].min(),
        df["latest_departure_hours"].max(),
    )
    tick_start = math.floor(range_min)
    tick_end = math.ceil(range_max)
    tickvals = list(range(tick_start, tick_end + 1))
    fig.update_coloraxes(
        colorbar_title_text="Viimane väljumisaeg",
        colorbar_tickvals=tickvals,
        colorbar_ticktext=[seconds_to_hhmm(v * 3600) for v in tickvals],
    )
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    return fig
