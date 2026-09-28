"""Pydantic schemas (request/response models) separate from ORM tables."""
from __future__ import annotations

from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import AppointmentStatus, Role


# ---- Auth ----
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    role: Role


# ---- Service ----
class ServiceCreate(BaseModel):
    name: str
    duration_min: int
    price: float
    category: str | None = None
    active: bool = True


class ServiceUpdate(BaseModel):
    name: str | None = None
    duration_min: int | None = None
    price: float | None = None
    category: str | None = None
    active: bool | None = None


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    duration_min: int
    price: float
    category: str | None = None
    active: bool


# ---- Working hours ----
class WorkingHoursCreate(BaseModel):
    weekday: int
    start: time
    end: time


class WorkingHoursOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    stylist_id: int
    weekday: int
    start: time
    end: time


# ---- Stylist ----
class StylistCreate(BaseModel):
    name: str
    bio: str | None = None
    active: bool = True
    service_ids: list[int] = []
    working_hours: list[WorkingHoursCreate] = []


class StylistUpdate(BaseModel):
    name: str | None = None
    bio: str | None = None
    active: bool | None = None
    service_ids: list[int] | None = None
    working_hours: list[WorkingHoursCreate] | None = None


class StylistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    bio: str | None = None
    active: bool
    services: list[ServiceOut] = []
    working_hours: list[WorkingHoursOut] = []


# ---- Availability ----
class SlotOut(BaseModel):
    start: datetime
    end: datetime


class AvailabilityOut(BaseModel):
    stylist_id: int
    service_id: int
    date: str
    slots: list[SlotOut]


# ---- Appointment ----
class AppointmentCreate(BaseModel):
    stylist_id: int
    service_id: int
    start: datetime


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    stylist_id: int
    service_id: int
    start: datetime
    end: datetime
    status: AppointmentStatus


class AppointmentDetailOut(AppointmentOut):
    service: ServiceOut | None = None
    stylist: StylistOut | None = None
