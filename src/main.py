"""Run the whole pipeline once, top to bottom. Mostly here to show the
order things get called in — for interactive parameter tweaking, use
main.ipynb instead.

    python3 main.py
"""

import clustering
import loading
import mapping
import search
import transfers
from constants import (
    ARRIVAL_DEADLINE,
    CLUSTERING_RADIUS_M,
    EARLIEST_DEPARTURE,
    MAX_ROUNDS,
    MAX_WALK_DISTANCE_M,
    SERVICE_DATE,
    TRANSFER_TIME_SEC,
    WALK_SPEED_KMH,
)

# --- 1. Load the feed ---
STOPS, TRIPS_DF, STOP_TIMES_DF, CALENDAR_DF, CALENDAR_DATES_DF = (
    loading.read_gtfs_tables()
)

# --- 2. Cluster nearby stops into dummy stops ---
clusters = clustering.build_clusters(STOPS, CLUSTERING_RADIUS_M)
dummy_stops = clustering.build_dummy_stops(STOPS, clusters, CLUSTERING_RADIUS_M)

# --- 3. Filter down to today's trips ---
trip_groups = loading.active_trip_groups(
    TRIPS_DF, STOP_TIMES_DF, CALENDAR_DF, CALENDAR_DATES_DF, SERVICE_DATE, clusters
)

# --- 4. Build walking connections between (dummy) stops ---
walk_speed_mps = WALK_SPEED_KMH * 1000 / 3600
walking_transfers = transfers.build_walking_transfers(
    dummy_stops, MAX_WALK_DISTANCE_M, walk_speed_mps
)

# --- 5. Run the reachability search ---
deadline_sec = mapping.hhmm_to_seconds(ARRIVAL_DEADLINE)
reach = search.compute_reach(
    trip_groups,
    walking_transfers,
    {"PAIDE", "TURI"},
    deadline_sec,
    TRANSFER_TIME_SEC,
    MAX_ROUNDS,
)
earliest_departure_sec = mapping.hhmm_to_seconds(EARLIEST_DEPARTURE)
reach = search.filter_by_earliest_departure(reach, earliest_departure_sec)

# --- 6. Summarize + draw the map ---
df = mapping.reach_to_dataframe(reach, dummy_stops)
print(f"Reachable: {len(reach)} / {len(dummy_stops)} (dummy) stops")

fig = mapping.build_map(df)
fig.write_html("map.html")
print("Wrote map.html")
