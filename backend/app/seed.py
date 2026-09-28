"""Seed the database with an admin user, sample services, stylists, and hours.

Run:  python -m app.seed
Idempotent: it clears existing services/stylists first, then inserts samples.
"""
from __future__ import annotations

from datetime import time

from sqlmodel import Session, select

from app.config import get_settings
from app.db import engine, init_db
from app.models import (
    Appointment,
    Customer,
    Role,
    Service,
    Stylist,
    StylistServiceLink,
    WorkingHours,
)
from app.security import hash_password

settings = get_settings()


def seed() -> None:
    init_db()
    with Session(engine) as session:
        # Reset domain tables (keep it simple and repeatable).
        for model in (Appointment, StylistServiceLink, WorkingHours, Stylist, Service):
            for row in session.exec(select(model)).all():
                session.delete(row)
        session.commit()

        # Admin user (create if missing).
        admin = session.exec(
            select(Customer).where(Customer.email == settings.admin_email)
        ).first()
        if not admin:
            admin = Customer(
                name="Salon Admin",
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                role=Role.admin,
            )
            session.add(admin)

        # Sample demo customer.
        demo = session.exec(
            select(Customer).where(Customer.email == "customer@salon.test")
        ).first()
        if not demo:
            session.add(
                Customer(
                    name="Demo Customer",
                    email="customer@salon.test",
                    password_hash=hash_password("customer123"),
                    role=Role.customer,
                )
            )

        # Services.
        services = [
            Service(name="Men's Cut", duration_min=30, price=30, category="Haircut"),
            Service(name="Women's Cut", duration_min=45, price=50, category="Haircut"),
            Service(name="Kids Cut", duration_min=20, price=20, category="Haircut"),
            Service(name="Beard Trim", duration_min=15, price=15, category="Grooming"),
            Service(name="Color & Highlights", duration_min=120, price=120, category="Color"),
        ]
        for s in services:
            session.add(s)
        session.commit()
        for s in services:
            session.refresh(s)

        # Weekday working hours Mon-Fri 9-17, Sat 10-15 (weekday: 0=Mon).
        def weekhours(morning=(9, 0), evening=(17, 0), sat=(10, 0), sat_end=(15, 0)):
            hours = []
            for wd in range(0, 5):  # Mon-Fri
                hours.append(WorkingHours(weekday=wd, start=time(*morning), end=time(*evening)))
            hours.append(WorkingHours(weekday=5, start=time(*sat), end=time(*sat_end)))
            return hours

        # Stylists with services + hours.
        alex = Stylist(name="Alex Rivera", bio="Fades & classic cuts")
        alex.services = [services[0], services[2], services[3]]
        alex.working_hours = weekhours()

        sam = Stylist(name="Sam Taylor", bio="Color specialist")
        sam.services = [services[1], services[4]]
        sam.working_hours = weekhours(morning=(10, 0), evening=(18, 0))

        jordan = Stylist(name="Jordan Lee", bio="All-rounder")
        jordan.services = list(services)
        jordan.working_hours = weekhours()

        session.add_all([alex, sam, jordan])
        session.commit()
        print("Seed complete: admin, demo customer, 5 services, 3 stylists.")


if __name__ == "__main__":
    seed()
