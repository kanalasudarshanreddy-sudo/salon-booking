"""Appointment booking, cancellation, and history."""
from __future__ import annotations

from datetime import datetime, timedelta

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
    appt.status = AppointmentStatus.cancelled
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return appt
