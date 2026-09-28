"""Unit tests for the pure availability engine."""
from datetime import datetime, time

from app.availability import Interval, generate_slots


DAY = datetime(2026, 1, 5)  # a Monday


def test_no_working_hours_returns_empty():
    slots = generate_slots(
        day=DAY, working_periods=[], existing=[], duration_min=30
    )
    assert slots == []


def test_basic_slots_generated():
    # 9:00-10:00, 30-min service, 30-min interval -> 09:00 and 09:30 starts.
    slots = generate_slots(
        day=DAY,
        working_periods=[(time(9, 0), time(10, 0))],
        existing=[],
        duration_min=30,
        slot_interval_min=30,
    )
    starts = [s.start for s in slots]
    assert starts == [datetime(2026, 1, 5, 9, 0), datetime(2026, 1, 5, 9, 30)]


def test_service_longer_than_window():
    # 60-min service in a 30-min window -> no slots.
    slots = generate_slots(
        day=DAY,
        working_periods=[(time(9, 0), time(9, 30))],
        existing=[],
        duration_min=60,
    )
    assert slots == []


def test_existing_booking_blocks_overlap():
    # 09:00-10:00 booked; 30-min service at 15-min interval within 09:00-11:00.
    existing = [Interval(datetime(2026, 1, 5, 9, 0), datetime(2026, 1, 5, 10, 0))]
    slots = generate_slots(
        day=DAY,
        working_periods=[(time(9, 0), time(11, 0))],
        existing=existing,
        duration_min=30,
        slot_interval_min=30,
    )
    starts = [s.start for s in slots]
    # 09:00 and 09:30 overlap the booking; 10:00 and 10:30 are free.
    assert datetime(2026, 1, 5, 9, 0) not in starts
    assert datetime(2026, 1, 5, 9, 30) not in starts
    assert datetime(2026, 1, 5, 10, 0) in starts
    assert datetime(2026, 1, 5, 10, 30) in starts


def test_fully_booked_returns_empty():
    existing = [Interval(datetime(2026, 1, 5, 9, 0), datetime(2026, 1, 5, 10, 0))]
    slots = generate_slots(
        day=DAY,
        working_periods=[(time(9, 0), time(10, 0))],
        existing=existing,
        duration_min=30,
        slot_interval_min=30,
    )
    assert slots == []


def test_buffer_blocks_adjacent_slot():
    # Booking 09:00-09:30 with 15-min buffer blocks a 09:30 start.
    existing = [Interval(datetime(2026, 1, 5, 9, 0), datetime(2026, 1, 5, 9, 30))]
    slots = generate_slots(
        day=DAY,
        working_periods=[(time(9, 0), time(11, 0))],
        existing=existing,
        duration_min=30,
        slot_interval_min=30,
        buffer_min=15,
    )
    starts = [s.start for s in slots]
    assert datetime(2026, 1, 5, 9, 30) not in starts  # blocked by buffer
    assert datetime(2026, 1, 5, 10, 0) in starts


def test_past_slots_excluded():
    now = datetime(2026, 1, 5, 9, 30)
    slots = generate_slots(
        day=DAY,
        working_periods=[(time(9, 0), time(11, 0))],
        existing=[],
        duration_min=30,
        slot_interval_min=30,
        now=now,
    )
    starts = [s.start for s in slots]
    assert datetime(2026, 1, 5, 9, 0) not in starts
    assert datetime(2026, 1, 5, 9, 30) in starts
