"""Loading the GTFS feed (call read_gtfs_tables once; it's the slow part, ~5s)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from constants import PATH_TO_GTFS, WEEKDAY_COLUMNS
from models import Stop


def _parse_time_column(series: pd.Series) -> pd.Series:
    """ "HH:MM:SS" -> seconds since midnight, for a whole column at once."""
    parts = series.str.split(":", expand=True).astype("int64")
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def read_gtfs_tables(feed_path: str | Path = PATH_TO_GTFS):
    """Read the GTFS CSVs we need, once. Returns plain stops + DataFrames."""
    feed_path = Path(feed_path)

    stops_df = pd.read_csv(
        feed_path / "stops.txt",
        dtype={"stop_id": str},
        usecols=["stop_id", "stop_name", "stop_lat", "stop_lon"],
    )
    stops = {
        r.stop_id: Stop(r.stop_id, r.stop_name, r.stop_lat, r.stop_lon)
        for r in stops_df.itertuples(index=False)
    }

    trips_df = pd.read_csv(
        feed_path / "trips.txt",
        dtype={"trip_id": str, "service_id": str},
        usecols=["trip_id", "service_id"],
    )

    stop_times_df = pd.read_csv(
        feed_path / "stop_times.txt",
        dtype={"trip_id": str, "stop_id": str},
        usecols=[
            "trip_id",
            "stop_id",
            "stop_sequence",
            "arrival_time",
            "departure_time",
        ],
    )
    stop_times_df["arr_sec"] = _parse_time_column(stop_times_df["arrival_time"])
    stop_times_df["dep_sec"] = _parse_time_column(stop_times_df["departure_time"])
    # Sorting once here means every later groupby (which preserves row
    # order within each group) sees stops in travel order for free.
    stop_times_df = stop_times_df.sort_values(["trip_id", "stop_sequence"])

    calendar_df = pd.read_csv(
        feed_path / "calendar.txt",
        dtype={"service_id": str, "start_date": str, "end_date": str},
    )

    calendar_dates_df = pd.read_csv(
        feed_path / "calendar_dates.txt", dtype={"service_id": str, "date": str}
    )

    return stops, trips_df, stop_times_df, calendar_df, calendar_dates_df


def active_service_ids(calendar_df, calendar_dates_df, service_date: date) -> set[str]:
    """Which service_ids run on this date: (regular weekly pattern + added
    exceptions) - removed exceptions.
    """
    date_str = service_date.strftime("%Y%m%d")
    weekday_col = WEEKDAY_COLUMNS[service_date.weekday()]

    regular = set()
    # Regular weekly patterns
    in_range = (calendar_df["start_date"] <= date_str) & (
        calendar_df["end_date"] >= date_str
    )
    running = calendar_df[weekday_col].astype(str) == "1"
    regular = set(calendar_df.loc[in_range & running, "service_id"])

    added, removed = set(), set()
    # Added/removed exceptions
    on_date = calendar_dates_df[calendar_dates_df["date"] == date_str]
    exception_type = on_date["exception_type"].astype(str)
    added = set(on_date.loc[exception_type == "1", "service_id"])
    removed = set(on_date.loc[exception_type == "2", "service_id"])

    return (regular | added) - removed


def active_trip_groups(
    trips_df,
    stop_times_df,
    calendar_df,
    calendar_dates_df,
    service_date: date,
    cluster_of: dict[str, str],
) -> list[list[tuple]]:
    """Stop-times for today's trips only, remapped to (dummy) stop_ids,
    one small list per trip: [(stop_id, arr_sec, dep_sec), ...] in travel
    order. Filtering to today's trips *before* grouping is what makes this
    faster than looping over every trip in the whole feed.
    """
    active_ids = active_service_ids(calendar_df, calendar_dates_df, service_date)
    active_trip_ids = set(
        trips_df.loc[trips_df["service_id"].isin(active_ids), "trip_id"]
    )

    today = stop_times_df[stop_times_df["trip_id"].isin(active_trip_ids)].copy()
    today["stop_id"] = today["stop_id"].map(cluster_of)

    # We only need three columns out of each, as plain
    # (stop_id, arr_sec, dep_sec) tuples, one per stop the trip visits.
    trip_groups = []
    for trip_id, trip_rows in today.groupby("trip_id", sort=False):
        stops_on_this_trip = list(
            zip(trip_rows["stop_id"], trip_rows["arr_sec"], trip_rows["dep_sec"])
        )
        trip_groups.append(stops_on_this_trip)

    return trip_groups
