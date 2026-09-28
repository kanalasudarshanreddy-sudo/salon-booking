"""Stylist management: public reads, admin-only writes.

Handles the stylist's offered services (M2M) and working hours.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db import get_session
from app.deps import require_admin
from app.models import Service, Stylist, WorkingHours
from app.schemas import StylistCreate, StylistOut, StylistUpdate

router = APIRouter(prefix="/stylists", tags=["stylists"])


def _apply_services(session: Session, stylist: Stylist, service_ids: list[int]) -> None:
    services = []
    for sid in service_ids:
        svc = session.get(Service, sid)
        if not svc:
            raise HTTPException(status_code=400, detail=f"Service {sid} not found")
        services.append(svc)
    stylist.services = services


def _apply_working_hours(stylist: Stylist, wh_list) -> None:
    stylist.working_hours = [
        WorkingHours(weekday=wh.weekday, start=wh.start, end=wh.end)
        for wh in wh_list
    ]


@router.get("", response_model=list[StylistOut])
def list_stylists(
    include_inactive: bool = False, session: Session = Depends(get_session)
) -> list[Stylist]:
    stmt = select(Stylist)
    if not include_inactive:
        stmt = stmt.where(Stylist.active == True)  # noqa: E712
    return list(session.exec(stmt).all())


@router.get("/{stylist_id}", response_model=StylistOut)
def get_stylist(stylist_id: int, session: Session = Depends(get_session)) -> Stylist:
    stylist = session.get(Stylist, stylist_id)
    if not stylist:
        raise HTTPException(status_code=404, detail="Stylist not found")
    return stylist


@router.post(
    "", response_model=StylistOut, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_stylist(
    data: StylistCreate, session: Session = Depends(get_session)
) -> Stylist:
    stylist = Stylist(name=data.name, bio=data.bio, active=data.active)
    _apply_services(session, stylist, data.service_ids)
    _apply_working_hours(stylist, data.working_hours)
    session.add(stylist)
    session.commit()
    session.refresh(stylist)
    return stylist


@router.patch(
    "/{stylist_id}", response_model=StylistOut,
    dependencies=[Depends(require_admin)],
)
def update_stylist(
    stylist_id: int, data: StylistUpdate, session: Session = Depends(get_session)
) -> Stylist:
    stylist = session.get(Stylist, stylist_id)
    if not stylist:
        raise HTTPException(status_code=404, detail="Stylist not found")
    if data.name is not None:
        stylist.name = data.name
    if data.bio is not None:
        stylist.bio = data.bio
    if data.active is not None:
        stylist.active = data.active
    if data.service_ids is not None:
        _apply_services(session, stylist, data.service_ids)
    if data.working_hours is not None:
        _apply_working_hours(stylist, data.working_hours)
    session.add(stylist)
    session.commit()
    session.refresh(stylist)
    return stylist


@router.delete(
    "/{stylist_id}", status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_stylist(stylist_id: int, session: Session = Depends(get_session)) -> None:
    stylist = session.get(Stylist, stylist_id)
    if not stylist:
        raise HTTPException(status_code=404, detail="Stylist not found")
    session.delete(stylist)
    session.commit()
