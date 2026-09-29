"""Appointment booking, cancellation, and history."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_session
from app.deps import get_current_user, require_admin
from app.models import (
    Appointment,
    AppointmentStatus,
    Customer,
    Service,
    Stylist,
    WorkingHours,
)
from app.schemas import AppointmentCreate, AppointmentDetailOut, AppointmentOut

router = APIRouter(prefix="/appointments", tags=["appointments"])
settings = get_settings()

# Grace period after an appointment's end during which a late arrival can still
# be checked in. The no-show/completed sweep also waits for this window so a
# background list fetch doesn't prematurely resolve an appointment mid-grace.
CHECK_IN_GRACE = timedelta(minutes=15)


def _salon_now() -> datetime:
    """Current wall-clock time in the salon's timezone, as naive datetime
    (matching the naive storage convention used across the app)."""
    try:
        zone = ZoneInfo(settings.salon_tz)
    except (ZoneInfoNotFoundError, ValueError):
        zone = None
    return datetime.now(zone).replace(tzinfo=None)


def _sweep_elapsed(session: Session) -> None:
    """Transition elapsed `booked` appointments to a terminal status.

    A booking is resolved once it is past its end time plus the check-in grace
    period, based on check-in:
    - checked in  -> completed (the customer attended)
    - not checked in -> no_show

    Runs lazily on list reads (the app has no background scheduler). Persists
    the new status so admin views and reports reflect reality.
    """
    cutoff = _salon_now() - CHECK_IN_GRACE
    elapsed = session.exec(
        select(Appointment).where(
            Appointment.status == AppointmentStatus.booked,
            Appointment.end < cutoff,
        )
    ).all()
    if not elapsed:
        return
    for appt in elapsed:
        appt.status = (
            AppointmentStatus.completed
            if appt.checked_in_at is not None
            else AppointmentStatus.no_show
        )
        session.add(appt)
    session.commit()


def _within_working_hours(session: Session, stylist_id: int, start: datetime, end: datetime) -> bool:
    weekday = start.weekday()
    rows = session.exec(
        select(WorkingHours).where(
            WorkingHours.stylist_id == stylist_id,
            WorkingHours.weekday == weekday,
        )
    ).all()
    for w in rows:
        period_start = datetime(start.year, start.month, start.day, w.start.hour, w.start.minute)
        period_end = datetime(start.year, start.month, start.day, w.end.hour, w.end.minute)
        if start >= period_start and end <= period_end:
            return True
    return False


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def create_appointment(
    data: AppointmentCreate,
    session: Session = Depends(get_session),
    user: Customer = Depends(get_current_user),
) -> Appointment:
    stylist = session.get(Stylist, data.stylist_id)
    if not stylist or not stylist.active:
        raise HTTPException(status_code=404, detail="Stylist not found")
    service = session.get(Service, data.service_id)
    if not service or not service.active:
        raise HTTPException(status_code=404, detail="Service not found")
    if service.id not in {s.id for s in stylist.services}:
        raise HTTPException(status_code=400, detail="Stylist does not offer this service")

    start = data.start
    # Normalize to naive UTC (storage convention).
    if start.tzinfo is not None:
        from datetime import timezone as _tz
        start = start.astimezone(_tz.utc).replace(tzinfo=None)
    end = start + timedelta(minutes=service.duration_min)

    if not _within_working_hours(session, stylist.id, start, end):
        raise HTTPException(status_code=400, detail="Requested time is outside working hours")

    buffer = timedelta(minutes=settings.booking_buffer_minutes)
    # Double-booking check: any overlapping non-cancelled appointment for this stylist.
    day_start = datetime(start.year, start.month, start.day)
    day_end = day_start + timedelta(days=1)
    same_day = session.exec(
        select(Appointment).where(
            Appointment.stylist_id == stylist.id,
            Appointment.status == AppointmentStatus.booked,
            Appointment.start >= day_start,
            Appointment.start < day_end,
        )
    ).all()
    for a in same_day:
        if start < (a.end + buffer) and (a.start - buffer) < end:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Time slot is no longer available",
            )

    appt = Appointment(
        customer_id=user.id,
        stylist_id=stylist.id,
        service_id=service.id,
        start=start,
        end=end,
        status=AppointmentStatus.booked,
    )
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return appt


@router.get("/me", response_model=list[AppointmentDetailOut])
def my_appointments(
    session: Session = Depends(get_session),
    user: Customer = Depends(get_current_user),
) -> list[Appointment]:
    _sweep_elapsed(session)
    rows = session.exec(
        select(Appointment)
        .where(Appointment.customer_id == user.id)
        .order_by(Appointment.start.desc())
    ).all()
    return list(rows)


@router.get("", response_model=list[AppointmentDetailOut], dependencies=[Depends(require_admin)])
def list_all_appointments(
    upcoming_only: bool = False,
    session: Session = Depends(get_session),
) -> list[Appointment]:
    _sweep_elapsed(session)
    stmt = select(Appointment)
    if upcoming_only:
        stmt = stmt.where(Appointment.start >= datetime.utcnow())
    stmt = stmt.order_by(Appointment.start.asc())
    return list(session.exec(stmt).all())


@router.patch("/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel_appointment(
    appointment_id: int,
    session: Session = Depends(get_session),
    user: Customer = Depends(get_current_user),
) -> Appointment:
    appt = session.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    # Owner or admin may cancel.
    if appt.customer_id != user.id and user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not allowed to cancel this appointment")
    if appt.status == AppointmentStatus.cancelled:
        return appt
    # Cannot cancel an appointment whose time has already passed — resolve its
    # terminal status (completed/no_show) and reject the cancel.
    if appt.end < _salon_now():
        _sweep_elapsed(session)
        session.refresh(appt)
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel an appointment that has already passed",
        )
    appt.status = AppointmentStatus.cancelled
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return appt


@router.patch(
    "/{appointment_id}/check-in",
    response_model=AppointmentOut,
    dependencies=[Depends(require_admin)],
)
def check_in_appointment(
    appointment_id: int,
    session: Session = Depends(get_session),
) -> Appointment:
    """Admin marks a customer as arrived. Records the salon-local arrival time."""
    appt = session.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.status != AppointmentStatus.booked:
        raise HTTPException(
            status_code=400,
            detail="Only booked appointments can be checked in",
        )
    if _salon_now() > appt.end + CHECK_IN_GRACE:
        raise HTTPException(
            status_code=400,
            detail="Check-in window has closed for this appointment",
        )
    if appt.checked_in_at is None:
        appt.checked_in_at = _salon_now()
        session.add(appt)
        session.commit()
        session.refresh(appt)
    return appt


@router.patch(
    "/{appointment_id}/undo-check-in",
    response_model=AppointmentOut,
    dependencies=[Depends(require_admin)],
)
def undo_check_in_appointment(
    appointment_id: int,
    session: Session = Depends(get_session),
) -> Appointment:
    """Admin clears a check-in (e.g. marked by mistake)."""
    appt = session.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.checked_in_at is not None:
        appt.checked_in_at = None
        session.add(appt)
        session.commit()
        session.refresh(appt)
    return appt
