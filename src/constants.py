# Paths
from datetime import date

PATH_TO_GTFS = "data/estonia_unified_gtfs"

EARTH_RADIUS_M = 6371000.0
NEG_INF = float("-inf")
WEEKDAY_COLUMNS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

# The stop_ids that make up each town, hand-picked.
# These always get merged into their own "PAIDE" / "TURI" dummy stop, no
# matter what the clustering radius is set to.
PAIDE_STOP_IDS = {
    "21356",
    "22316",
    "29452",  # Paide kutsekool, Paide bussijaam
    "132376",
    "132415",
    "132419",
    "132424",
    "132430",
    "132436",  # bussijaam 1-6
}
TURI_STOP_IDS = {"24640", "24650", "27807", "28982", "28983", "34050", "34143"}

# Default parameters
SERVICE_DATE = date(2026, 8, 8)
ARRIVAL_DEADLINE = "09:45"  # "HH:MM"
TRANSFER_TIME_SEC = 300
MAX_WALK_DISTANCE_M = 5000
WALK_SPEED_KMH = 5.0
MAX_ROUNDS = 2
EARLIEST_DEPARTURE = "07:00"  # "HH:MM", or None for no floor
CLUSTERING_RADIUS_M = 7500
