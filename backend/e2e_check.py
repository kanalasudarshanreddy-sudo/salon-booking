"""End-to-end integration check against a RUNNING backend.

Prereqs: backend running (e.g. `python -m uvicorn app.main:app --port 8000`)
and seeded (`python -m app.seed`).

Usage:
    python e2e_check.py [BASE_URL]
Defaults to http://127.0.0.1:8000

Flow: public reads -> register customer -> availability -> book ->
verify slot disappears -> history -> cancel -> verify slot returns.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def next_working_day_iso() -> str:
    d = datetime.utcnow().date()
    # Seeded stylists work Mon-Sat; skip Sunday (weekday 6).
    while d.weekday() == 6:
        d += timedelta(days=1)
    # Use a day at least 1 day out to avoid past-slot filtering.
    d += timedelta(days=1)
    while d.weekday() == 6:
        d += timedelta(days=1)
    return d.isoformat()


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=10) as c:
        # 1. Health
        assert c.get("/health").json() == {"status": "ok"}, "health failed"

        # 2. Public reads
        services = c.get("/services").json()
        stylists = c.get("/stylists").json()
        assert services, "no services seeded"
        assert stylists, "no stylists seeded"

        # Pick a stylist + a service that stylist offers.
        stylist = next((s for s in stylists if s["services"]), None)
        assert stylist, "no stylist offers a service"
        service = stylist["services"][0]
        print(f"Using stylist '{stylist['name']}' + service '{service['name']}'")

        # 3. Register a fresh customer
        email = f"e2e_{uuid.uuid4().hex[:8]}@test.com"
        reg = c.post(
            "/auth/register",
            json={"name": "E2E", "email": email, "password": "password123"},
        )
        assert reg.status_code == 201, f"register failed: {reg.text}"
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 4. Availability
        date = next_working_day_iso()
        av = c.get(
            "/availability",
            params={"stylist_id": stylist["id"], "service_id": service["id"], "date": date},
        ).json()
        slots_before = av["slots"]
        assert slots_before, f"no slots on {date}"
        first = slots_before[0]["start"]
        print(f"{len(slots_before)} slots on {date}; booking {first}")

        # 5. Book
        book = c.post(
            "/appointments",
            json={"stylist_id": stylist["id"], "service_id": service["id"], "start": first},
            headers=headers,
        )
        assert book.status_code == 201, f"book failed: {book.text}"
        appt_id = book.json()["id"]

        # 6. Slot disappears
        av2 = c.get(
            "/availability",
            params={"stylist_id": stylist["id"], "service_id": service["id"], "date": date},
        ).json()
        assert len(av2["slots"]) < len(slots_before), "slot did not disappear"

        # 7. Double booking rejected
        dup = c.post(
            "/appointments",
            json={"stylist_id": stylist["id"], "service_id": service["id"], "start": first},
            headers=headers,
        )
        assert dup.status_code == 409, f"expected 409, got {dup.status_code}"

        # 8. History
        hist = c.get("/appointments/me", headers=headers).json()
        assert any(a["id"] == appt_id for a in hist), "booking missing from history"

        # 9. Cancel -> slot returns
        cancel = c.patch(f"/appointments/{appt_id}/cancel", headers=headers)
        assert cancel.status_code == 200 and cancel.json()["status"] == "cancelled"
        av3 = c.get(
            "/availability",
            params={"stylist_id": stylist["id"], "service_id": service["id"], "date": date},
        ).json()
        assert len(av3["slots"]) == len(slots_before), "slot did not return after cancel"

    print("E2E PASSED: register -> book -> verify -> cancel all succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
