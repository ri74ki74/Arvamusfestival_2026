"""Animate how the reachable area shrinks as the earliest-you're-willing-
to-leave time increases, from SWEEP_START_HOUR up to SWEEP_END_HOUR, in
5-minute steps. Saves one PNG per step, then stitches them into a GIF.

compute_reach only depends on the arrival deadline, not on the earliest-
departure floor, so it's run once here and just re-filtered per frame —
much cheaper than re-running the whole search 41 times.
"""

from pathlib import Path

import clustering
import loading
import mapping
import search
import transfers
from constants import (
    ARRIVAL_DEADLINE,
    CLUSTERING_RADIUS_M,
    MAX_ROUNDS,
    MAX_WALK_DISTANCE_M,
    SERVICE_DATE,
    TRANSFER_TIME_SEC,
    WALK_SPEED_KMH,
)
from PIL import Image

STEP_MINUTES = 5
SWEEP_START_HOUR = 4.0
SWEEP_END_HOUR = 10.0
FRAMES_DIR = Path("gif_frames")
GIF_PATH = Path("reachability.gif")

# --- Everything that doesn't depend on the earliest-departure sweep, built once ---
STOPS, TRIPS_DF, STOP_TIMES_DF, CALENDAR_DF, CALENDAR_DATES_DF = (
    loading.read_gtfs_tables()
)
clusters = clustering.build_clusters(STOPS, CLUSTERING_RADIUS_M)
dummy_stops = clustering.build_dummy_stops(STOPS, clusters, CLUSTERING_RADIUS_M)

trip_groups = loading.active_trip_groups(
    TRIPS_DF, STOP_TIMES_DF, CALENDAR_DF, CALENDAR_DATES_DF, SERVICE_DATE, clusters
)

walk_speed_mps = WALK_SPEED_KMH * 1000 / 3600
walking_transfers = transfers.build_walking_transfers(
    dummy_stops, MAX_WALK_DISTANCE_M, walk_speed_mps
)

deadline_sec = mapping.hhmm_to_seconds(ARRIVAL_DEADLINE)
reach = search.compute_reach(
    trip_groups,
    walking_transfers,
    {"PAIDE", "TURI"},
    deadline_sec,
    TRANSFER_TIME_SEC,
    MAX_ROUNDS,
)

# Fixed color scale + map framing for every frame, from the full
# (unfiltered) result — so only the dots change from frame to frame, not
# the scale or where the map is centered.
full_df = mapping.reach_to_dataframe(reach, dummy_stops)
color_range = (
    full_df["latest_departure_hours"].min(),
    full_df["latest_departure_hours"].max(),
)
map_center = {"lat": full_df["lat"].mean(), "lon": full_df["lon"].mean()}

# --- One frame per 5-minute step ---
FRAMES_DIR.mkdir(exist_ok=True)
frame_paths = []

n_steps = int((SWEEP_END_HOUR - SWEEP_START_HOUR) * 60 / STEP_MINUTES) + 1
for i in range(n_steps):
    hour = SWEEP_START_HOUR + i * STEP_MINUTES / 60
    earliest_departure_sec = int(hour * 3600)

    filtered_reach = search.filter_by_earliest_departure(reach, earliest_departure_sec)
    df = mapping.reach_to_dataframe(filtered_reach, dummy_stops)

    hhmm = mapping.seconds_to_hhmm(earliest_departure_sec)

    fig = mapping.build_map(df, color_range=color_range, center=map_center)
    fig.update_layout(title=f"Varaseim väljumisaeg: {hhmm} — {len(df)} peatust")

    frame_path = FRAMES_DIR / f"frame_{i:03d}.png"
    fig.write_image(frame_path, width=1000, height=700, scale=2)
    frame_paths.append(frame_path)
    print(f"{hhmm}: {len(df)} peatust -> {frame_path}")

# --- Stitch the frames into a GIF ---
images = [Image.open(p) for p in frame_paths]
images[0].save(
    GIF_PATH,
    save_all=True,
    append_images=images[1:],
    duration=300,  # ms per frame
    loop=0,
)
print(f"Wrote {GIF_PATH}")
