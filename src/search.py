"""The core reachability search.

Works backwards from the deadline: reach[stop] = the latest time you
could leave that stop and still get to a target stop by the deadline.
Each round adds one more transit ride (plus at most one walk) to what's
reachable, up to max_rounds.

Here currently the iterative method could be improved: at this point
we go over the target stops for 'max_rounds' times, for immediate
neighbors for 'max_rounds' - 1 times etc. But since it's quite fast anyway,
I decidede not to up the complexity for marginal gains.
"""

from __future__ import annotations

from constants import NEG_INF


def _relax_trips(trip_groups, previous, reach, transfer_buffer_sec) -> bool:
    """One transit ride per trip. Two plain passes over each trip's stops:

    1. Find the furthest-along stop this trip already reaches something
       useful from (per `previous`) — if none, this trip helps nobody.
    2. Every earlier stop on the trip can board here and ride to it, so
       give each one a candidate departure time.

    Returns whether anything in `reach` got updated.
    """
    changed = False
    for stop_times in trip_groups:
        last_usable_index = None
        for i, (stop_id, arr_sec, _dep_sec) in enumerate(stop_times):
            if arr_sec <= previous.get(stop_id, NEG_INF):
                last_usable_index = i

        if last_usable_index is None:
            continue  # nothing on this trip connects to anything reachable

        for stop_id, _arr_sec, dep_sec in stop_times[:last_usable_index]:
            candidate = dep_sec - transfer_buffer_sec
            if candidate > reach.get(stop_id, NEG_INF):
                reach[stop_id] = candidate
                changed = True
    return changed


def _relax_walks(transfers, reach) -> bool:
    """At most one walking leg per round. Reads from a snapshot taken
    *before* this loop, so two edges can't chain together into two
    walking legs within the same round. Returns whether anything in
    `reach` got updated.
    """
    changed = False
    walk_snapshot = dict(reach)
    for from_id, to_id, walk_time_sec in transfers:
        to_reach = walk_snapshot.get(to_id)
        if to_reach is None:
            continue
        candidate = to_reach - walk_time_sec
        if candidate > reach.get(from_id, NEG_INF):
            reach[from_id] = candidate
            changed = True
    return changed


def compute_reach(
    trip_groups, transfers, target_ids, deadline_sec, transfer_buffer_sec, max_rounds
):
    reach = {stop_id: deadline_sec for stop_id in target_ids}

    for _ in range(max_rounds):
        previous = dict(reach)  # snapshot from before this round
        trip_changed = _relax_trips(trip_groups, previous, reach, transfer_buffer_sec)
        walk_changed = _relax_walks(transfers, reach)
        if not (trip_changed or walk_changed):
            break

    return reach


def filter_by_earliest_departure(
    reach: dict[str, int], earliest_departure_sec: int | None
) -> dict[str, int]:
    """Drop any stop whose only way to reach the target requires leaving
    before earliest_departure_sec. None means no floor: keep everything as
    compute_reach found it.
    """
    if earliest_departure_sec is None:
        return reach
    return {
        stop_id: latest_departure
        for stop_id, latest_departure in reach.items()
        if latest_departure >= earliest_departure_sec
    }
