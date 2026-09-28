"""Service management: public reads, admin-only writes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db import get_session
from app.deps import require_admin
from app.models import Service
from app.schemas import ServiceCreate, ServiceOut, ServiceUpdate

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=list[ServiceOut])
def list_services(
    include_inactive: bool = False, session: Session = Depends(get_session)
) -> list[Service]:
    stmt = select(Service)
    if not include_inactive:
        stmt = stmt.where(Service.active == True)  # noqa: E712
    return list(session.exec(stmt).all())


@router.get("/{service_id}", response_model=ServiceOut)
def get_service(service_id: int, session: Session = Depends(get_session)) -> Service:
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@router.post(
    "", response_model=ServiceOut, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_service(
    data: ServiceCreate, session: Session = Depends(get_session)
) -> Service:
    service = Service(**data.model_dump())
    session.add(service)
    session.commit()
    session.refresh(service)
    return service


@router.patch(
    "/{service_id}", response_model=ServiceOut,
    dependencies=[Depends(require_admin)],
)
def update_service(
    service_id: int, data: ServiceUpdate, session: Session = Depends(get_session)
) -> Service:
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(service, key, value)
    session.add(service)
    session.commit()
    session.refresh(service)
    return service


@router.delete(
    "/{service_id}", status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_service(service_id: int, session: Session = Depends(get_session)) -> None:
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    session.delete(service)
    session.commit()
