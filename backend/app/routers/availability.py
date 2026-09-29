"""Availability endpoint: computes open slots for a stylist/service/date."""
from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.availability import Interval, generate_slots
from app.config import get_settings
from app.db import get_session
from app.models import Appointment, AppointmentStatus, Service, Stylist, WorkingHours
from app.schemas import AvailabilityOut, SlotOut

router = APIRouter(prefix="/availability", tags=["availability"])
settings = get_settings()


@router.get("", response_model=AvailabilityOut)
def get_availability(
    stylist_id: int = Query(...),
    service_id: int = Query(...),
    date: date_cls = Query(..., description="YYYY-MM-DD"),
    session: Session = Depends(get_session),
) -> AvailabilityOut:
    stylist = session.get(Stylist, stylist_id)
    if not stylist or not stylist.active:
        raise HTTPException(status_code=404, detail="Stylist not found")
    service = session.get(Service, service_id)
    if not service or not service.active:
        raise HTTPException(status_code=404, detail="Service not found")

    # Ensure the stylist offers this service.
    if service.id not in {s.id for s in stylist.services}:
        raise HTTPException(
            status_code=400, detail="Stylist does not offer this service"
        )

    weekday = date.weekday()  # 0=Monday
    wh_rows = session.exec(
        select(WorkingHours).where(
            WorkingHours.stylist_id == stylist_id,
            WorkingHours.weekday == weekday,
        )
    ).all()
    working_periods: list[tuple[time, time]] = [(w.start, w.end) for w in wh_rows]

    # Existing (non-cancelled) bookings that day.
    day_start = datetime(date.year, date.month, date.day)
    day_end = datetime(date.year, date.month, date.day, 23, 59, 59)
    appts = session.exec(
        select(Appointment).where(
            Appointment.stylist_id == stylist_id,
            Appointment.status == AppointmentStatus.booked,
            Appointment.start >= day_start,
            Appointment.start <= day_end,
        )
    ).all()
    existing = [Interval(start=a.start, end=a.end) for a in appts]

    # Current time as the salon's local wall-clock time, stored naive to match
    # the naive working-hours slots. This makes the "hide past slots" cutoff
    # align with the salon's actual clock regardless of server/UTC timezone.
    # For future dates every slot is after `now` (no effect); for past dates all
    # slots are before `now` (correctly empty).
    try:
        salon_zone = ZoneInfo(settings.salon_tz)
    except (ZoneInfoNotFoundError, ValueError):
        salon_zone = None
    now = datetime.now(salon_zone).replace(tzinfo=None)

    slots = generate_slots(
        day=day_start,
        working_periods=working_periods,
        existing=existing,
        duration_min=service.duration_min,
        slot_interval_min=settings.slot_interval_minutes,
        buffer_min=settings.booking_buffer_minutes,
        now=now,
    )

    return AvailabilityOut(
        stylist_id=stylist_id,
        service_id=service_id,
        date=date.isoformat(),
        slots=[SlotOut(start=s.start, end=s.end) for s in slots],
    )
