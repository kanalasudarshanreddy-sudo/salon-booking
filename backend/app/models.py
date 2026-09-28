"""SQLModel ORM entities for the salon booking domain.

Note: we intentionally do NOT use `from __future__ import annotations` here.
SQLModel relies on evaluated (non-postponed) annotations to configure
relationships correctly under SQLAlchemy 2.0.
"""
from datetime import datetime, time
from enum import Enum
from typing import List, Optional

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel


class Role(str, Enum):
    customer = "customer"
    admin = "admin"


class AppointmentStatus(str, Enum):
    booked = "booked"
    cancelled = "cancelled"
    completed = "completed"


class StylistServiceLink(SQLModel, table=True):
    """Many-to-many link between stylists and the services they offer."""

    __tablename__ = "stylist_service_link"

    stylist_id: Optional[int] = Field(
        default=None, foreign_key="stylist.id", primary_key=True
    )
    service_id: Optional[int] = Field(
        default=None, foreign_key="service.id", primary_key=True
    )


class Customer(SQLModel, table=True):
    __tablename__ = "customer"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: Role = Field(default=Role.customer)
    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime)
    )

    appointments: List["Appointment"] = Relationship(back_populates="customer")


class Service(SQLModel, table=True):
    __tablename__ = "service"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    duration_min: int
    price: float
    category: Optional[str] = None
    active: bool = Field(default=True)

    stylists: List["Stylist"] = Relationship(
        back_populates="services", link_model=StylistServiceLink
    )
    appointments: List["Appointment"] = Relationship(back_populates="service")


class Stylist(SQLModel, table=True):
    __tablename__ = "stylist"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    bio: Optional[str] = None
    active: bool = Field(default=True)

    services: List[Service] = Relationship(
        back_populates="stylists", link_model=StylistServiceLink
    )
    working_hours: List["WorkingHours"] = Relationship(
        back_populates="stylist",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    appointments: List["Appointment"] = Relationship(back_populates="stylist")


class WorkingHours(SQLModel, table=True):
    __tablename__ = "working_hours"

    id: Optional[int] = Field(default=None, primary_key=True)
    stylist_id: int = Field(foreign_key="stylist.id", index=True)
    weekday: int = Field(description="0=Monday ... 6=Sunday")
    start: time
    end: time

    stylist: Optional[Stylist] = Relationship(back_populates="working_hours")


class Appointment(SQLModel, table=True):
    __tablename__ = "appointment"

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id", index=True)
    stylist_id: int = Field(foreign_key="stylist.id", index=True)
    service_id: int = Field(foreign_key="service.id", index=True)
    start: datetime = Field(sa_column=Column(DateTime, index=True))
    end: datetime = Field(sa_column=Column(DateTime))
    status: AppointmentStatus = Field(default=AppointmentStatus.booked)
    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime)
    )

    customer: Optional[Customer] = Relationship(back_populates="appointments")
    stylist: Optional[Stylist] = Relationship(back_populates="appointments")
    service: Optional[Service] = Relationship(back_populates="appointments")
