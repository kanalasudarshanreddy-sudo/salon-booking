"""Pure availability computation, decoupled from HTTP and the database.

All datetimes are treated as naive UTC for storage/comparison consistency.
The engine takes plain data (working intervals + existing bookings) and returns
the list of bookable start/end slots for a service of a given duration.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class Slot:
    start: datetime
    end: datetime


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Half-open interval overlap test: [a_start, a_end) vs [b_start, b_end)."""
    return a_start < b_end and b_start < a_end


def generate_slots(
    *,
    day: datetime,
    working_periods: list[tuple[time, time]],
    existing: list[Interval],
    duration_min: int,
    slot_interval_min: int = 15,
    buffer_min: int = 0,
    now: datetime | None = None,
) -> list[Slot]:
    """Compute bookable slots for a single day.

    Args:
        day: the date (time component ignored) to compute slots for.
        working_periods: list of (start_time, end_time) the stylist works that day.
        existing: existing booked intervals (should be that day's bookings).
        duration_min: length of the service being booked.
        slot_interval_min: granularity of candidate start times (e.g. every 15 min).
        buffer_min: buffer added around each existing booking when checking conflicts.
        now: if provided, slots starting before `now` are excluded (no past booking).

    Returns:
        Sorted list of non-conflicting Slot(start, end).
    """
    if duration_min <= 0:
        return []
    if slot_interval_min <= 0:
        slot_interval_min = duration_min

    duration = timedelta(minutes=duration_min)
    step = timedelta(minutes=slot_interval_min)
    buffer = timedelta(minutes=buffer_min)
    base = datetime(day.year, day.month, day.day)

    slots: list[Slot] = []
    for start_t, end_t in working_periods:
        period_start = base + timedelta(hours=start_t.hour, minutes=start_t.minute)
        period_end = base + timedelta(hours=end_t.hour, minutes=end_t.minute)
        if period_end <= period_start:
            continue

        candidate = period_start
        while candidate + duration <= period_end:
            slot_end = candidate + duration
            # Skip past slots.
            if now is not None and candidate < now:
                candidate += step
                continue
            # Conflict check against existing bookings (with buffer).
            conflict = any(
                _overlaps(
                    candidate,
                    slot_end,
                    ex.start - buffer,
                    ex.end + buffer,
                )
                for ex in existing
            )
            if not conflict:
                slots.append(Slot(start=candidate, end=slot_end))
            candidate += step

    slots.sort(key=lambda s: s.start)
    return slots
