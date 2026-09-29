"""API-level tests: health, auth/roles, CRUD guards, availability, booking."""
from __future__ import annotations

from datetime import datetime, timedelta

from tests.conftest import auth_header, make_admin_token, register


def _next_monday_9am() -> datetime:
    d = datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0)
    # advance to a future Monday
    while d.weekday() != 0 or d <= datetime.utcnow():
        d += timedelta(days=1)
    return d


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_register_login_me(client):
    r = register(client, email="a@test.com")
    assert r.status_code == 201
    token = r.json()["access_token"]

    me = client.get("/auth/me", headers=auth_header(token))
    assert me.status_code == 200
    assert me.json()["email"] == "a@test.com"
    assert me.json()["role"] == "customer"


def test_login_bad_credentials(client):
    register(client, email="b@test.com", password="password123")
    r = client.post("/auth/login", data={"username": "b@test.com", "password": "wrong"})
    assert r.status_code == 401


def test_duplicate_email_rejected(client):
    register(client, email="dup@test.com")
    r = register(client, email="dup@test.com")
    assert r.status_code == 409


def test_non_admin_cannot_create_service(client):
    token = register(client, email="c@test.com").json()["access_token"]
    r = client.post(
        "/services",
        json={"name": "X", "duration_min": 30, "price": 10},
        headers=auth_header(token),
    )
    assert r.status_code == 403


def test_admin_crud_and_public_read(client):
    admin = make_admin_token(client)
    r = client.post(
        "/services",
        json={"name": "Men's Cut", "duration_min": 30, "price": 30, "category": "Haircut"},
        headers=auth_header(admin),
    )
    assert r.status_code == 201
    sid = r.json()["id"]

    # Public read (no auth).
    lst = client.get("/services")
    assert lst.status_code == 200
    assert any(s["id"] == sid for s in lst.json())


def test_booking_flow_and_double_booking(client):
    admin = make_admin_token(client)
    # Service.
    svc = client.post(
        "/services",
        json={"name": "Cut", "duration_min": 30, "price": 30},
        headers=auth_header(admin),
    ).json()
    # Stylist offering the service, working Mondays 9-17.
    stylist = client.post(
        "/stylists",
        json={
            "name": "Alex",
            "service_ids": [svc["id"]],
            "working_hours": [{"weekday": 0, "start": "09:00:00", "end": "17:00:00"}],
        },
        headers=auth_header(admin),
    ).json()

    monday = _next_monday_9am()
    date_str = monday.date().isoformat()

    # Availability before booking.
    avail = client.get(
        "/availability",
        params={"stylist_id": stylist["id"], "service_id": svc["id"], "date": date_str},
    )
    assert avail.status_code == 200
    slots_before = avail.json()["slots"]
    assert len(slots_before) > 0

    # Customer books the first slot.
    cust = register(client, email="cust@test.com").json()["access_token"]
    first_start = slots_before[0]["start"]
    book = client.post(
        "/appointments",
        json={"stylist_id": stylist["id"], "service_id": svc["id"], "start": first_start},
        headers=auth_header(cust),
    )
    assert book.status_code == 201
    appt_id = book.json()["id"]

    # Double-booking same slot -> 409.
    dup = client.post(
        "/appointments",
        json={"stylist_id": stylist["id"], "service_id": svc["id"], "start": first_start},
        headers=auth_header(cust),
    )
    assert dup.status_code == 409

    # Slot count decreased after booking.
    avail2 = client.get(
        "/availability",
        params={"stylist_id": stylist["id"], "service_id": svc["id"], "date": date_str},
    ).json()
    assert len(avail2["slots"]) < len(slots_before)

    # History shows it.
    hist = client.get("/appointments/me", headers=auth_header(cust))
    assert hist.status_code == 200
    assert any(a["id"] == appt_id for a in hist.json())

    # Cancel frees the slot.
    cancel = client.patch(f"/appointments/{appt_id}/cancel", headers=auth_header(cust))
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"

    avail3 = client.get(
        "/availability",
        params={"stylist_id": stylist["id"], "service_id": svc["id"], "date": date_str},
    ).json()
    assert len(avail3["slots"]) == len(slots_before)


def test_cannot_cancel_others_appointment(client):
    admin = make_admin_token(client)
    svc = client.post(
        "/services", json={"name": "Cut", "duration_min": 30, "price": 30},
        headers=auth_header(admin),
    ).json()
    stylist = client.post(
        "/stylists",
        json={
            "name": "Alex", "service_ids": [svc["id"]],
            "working_hours": [{"weekday": 0, "start": "09:00:00", "end": "17:00:00"}],
        },
        headers=auth_header(admin),
    ).json()
    monday = _next_monday_9am()
    slot = client.get(
        "/availability",
        params={"stylist_id": stylist["id"], "service_id": svc["id"], "date": monday.date().isoformat()},
    ).json()["slots"][0]["start"]

    owner = register(client, email="owner@test.com").json()["access_token"]
    appt = client.post(
        "/appointments",
        json={"stylist_id": stylist["id"], "service_id": svc["id"], "start": slot},
        headers=auth_header(owner),
    ).json()

    other = register(client, email="other@test.com").json()["access_token"]
    r = client.patch(f"/appointments/{appt['id']}/cancel", headers=auth_header(other))
    assert r.status_code == 403


def test_check_in_flow(client):
    admin = make_admin_token(client)
    svc = client.post(
        "/services", json={"name": "Cut", "duration_min": 30, "price": 30},
        headers=auth_header(admin),
    ).json()
    stylist = client.post(
        "/stylists",
        json={
            "name": "Alex", "service_ids": [svc["id"]],
            "working_hours": [{"weekday": 0, "start": "09:00:00", "end": "17:00:00"}],
        },
        headers=auth_header(admin),
    ).json()
    monday = _next_monday_9am()
    slot = client.get(
        "/availability",
        params={"stylist_id": stylist["id"], "service_id": svc["id"], "date": monday.date().isoformat()},
    ).json()["slots"][0]["start"]

    cust = register(client, email="cust@test.com").json()["access_token"]
    appt = client.post(
        "/appointments",
        json={"stylist_id": stylist["id"], "service_id": svc["id"], "start": slot},
        headers=auth_header(cust),
    ).json()
    appt_id = appt["id"]
    assert appt["checked_in_at"] is None

    # Customer cannot check in (admin-only).
    forbidden = client.patch(
        f"/appointments/{appt_id}/check-in", headers=auth_header(cust)
    )
    assert forbidden.status_code == 403

    # Admin checks in -> records timestamp.
    ok = client.patch(f"/appointments/{appt_id}/check-in", headers=auth_header(admin))
    assert ok.status_code == 200
    assert ok.json()["checked_in_at"] is not None

    # Idempotent: checking in again keeps the same (non-null) value.
    again = client.patch(f"/appointments/{appt_id}/check-in", headers=auth_header(admin))
    assert again.status_code == 200
    assert again.json()["checked_in_at"] == ok.json()["checked_in_at"]

    # Undo clears it.
    undo = client.patch(
        f"/appointments/{appt_id}/undo-check-in", headers=auth_header(admin)
    )
    assert undo.status_code == 200
    assert undo.json()["checked_in_at"] is None


def test_cannot_check_in_cancelled_appointment(client):
    admin = make_admin_token(client)
    svc = client.post(
        "/services", json={"name": "Cut", "duration_min": 30, "price": 30},
        headers=auth_header(admin),
    ).json()
    stylist = client.post(
        "/stylists",
        json={
            "name": "Alex", "service_ids": [svc["id"]],
            "working_hours": [{"weekday": 0, "start": "09:00:00", "end": "17:00:00"}],
        },
        headers=auth_header(admin),
    ).json()
    monday = _next_monday_9am()
    slot = client.get(
        "/availability",
        params={"stylist_id": stylist["id"], "service_id": svc["id"], "date": monday.date().isoformat()},
    ).json()["slots"][0]["start"]

    cust = register(client, email="cust2@test.com").json()["access_token"]
    appt = client.post(
        "/appointments",
        json={"stylist_id": stylist["id"], "service_id": svc["id"], "start": slot},
        headers=auth_header(cust),
    ).json()
    client.patch(f"/appointments/{appt['id']}/cancel", headers=auth_header(cust))

    # Cannot check in a cancelled appointment.
    r = client.patch(f"/appointments/{appt['id']}/check-in", headers=auth_header(admin))
    assert r.status_code == 400


def _seed_customer_and_appt(client, *, end_offset_min, checked_in):
    """Insert an appointment directly with a chosen end time relative to now.

    Bypasses the booking endpoint (which enforces future/working-hours) so we
    can create already-elapsed appointments for sweep tests.
    """
    from app import db as db_module
    from app.models import Appointment, AppointmentStatus, Customer, Service, Stylist
    from app.routers.appointments import _salon_now
    from sqlmodel import Session

    with Session(db_module.engine) as session:
        cust = Customer(name="C", email=f"sweep{end_offset_min}_{checked_in}@test.com",
                        password_hash="x")
        svc = Service(name="S", duration_min=30, price=10)
        sty = Stylist(name="St")
        session.add_all([cust, svc, sty])
        session.commit()
        session.refresh(cust); session.refresh(svc); session.refresh(sty)
        now = _salon_now()
        end = now + timedelta(minutes=end_offset_min)
        start = end - timedelta(minutes=30)
        appt = Appointment(
            customer_id=cust.id, stylist_id=sty.id, service_id=svc.id,
            start=start, end=end, status=AppointmentStatus.booked,
            checked_in_at=(now - timedelta(minutes=40)) if checked_in else None,
        )
        session.add(appt)
        session.commit()
        session.refresh(appt)
        return appt.id


def test_sweep_elapsed_checked_in_becomes_completed(client):
    admin = make_admin_token(client)
    appt_id = _seed_customer_and_appt(client, end_offset_min=-10, checked_in=True)
    appts = client.get("/appointments", headers=auth_header(admin)).json()
    row = next(a for a in appts if a["id"] == appt_id)
    assert row["status"] == "completed"


def test_sweep_elapsed_not_checked_in_becomes_no_show(client):
    admin = make_admin_token(client)
    appt_id = _seed_customer_and_appt(client, end_offset_min=-10, checked_in=False)
    appts = client.get("/appointments", headers=auth_header(admin)).json()
    row = next(a for a in appts if a["id"] == appt_id)
    assert row["status"] == "no_show"


def test_sweep_future_stays_booked(client):
    admin = make_admin_token(client)
    appt_id = _seed_customer_and_appt(client, end_offset_min=120, checked_in=False)
    appts = client.get("/appointments", headers=auth_header(admin)).json()
    row = next(a for a in appts if a["id"] == appt_id)
    assert row["status"] == "booked"
