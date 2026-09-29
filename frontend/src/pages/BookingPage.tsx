import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api'
import { useAuth } from '../auth'
import type { Service, Slot, Stylist } from '../types'

function todayISO(): string {
  return new Date().toISOString().slice(0, 10)
}

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Bucket slots into time-of-day groups for easier scanning.
// Uses the slot's start hour (naive-UTC ISO parsed consistently with fmtTime).
const SLOT_GROUPS: { label: string; test: (hour: number) => boolean }[] = [
  { label: 'Morning', test: (h) => h < 12 },
  { label: 'Afternoon', test: (h) => h >= 12 && h < 17 },
  { label: 'Evening', test: (h) => h >= 17 },
]

function groupSlots(slots: Slot[]): { label: string; slots: Slot[] }[] {
  return SLOT_GROUPS.map((g) => ({
    label: g.label,
    slots: slots.filter((s) => g.test(new Date(s.start).getHours())),
  })).filter((g) => g.slots.length > 0)
}

export default function BookingPage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [services, setServices] = useState<Service[]>([])
  const [stylists, setStylists] = useState<Stylist[]>([])
  const [serviceId, setServiceId] = useState<number | null>(null)
  const [stylistId, setStylistId] = useState<number | null>(null)
  const [date, setDate] = useState<string>(todayISO())
  const [slots, setSlots] = useState<Slot[]>([])
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null)
  const [booking, setBooking] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api.listServices(), api.listStylists()])
      .then(([s, st]) => {
        setServices(s)
        setStylists(st)
      })
      .catch((e) => setError(e.message))
  }, [])

  // Stylists that offer the chosen service.
  const eligibleStylists = useMemo(() => {
    if (!serviceId) return stylists
    return stylists.filter((st) => st.services.some((sv) => sv.id === serviceId))
  }, [stylists, serviceId])

  const selectedService = useMemo(
    () => services.find((s) => s.id === serviceId) ?? null,
    [services, serviceId],
  )
  const selectedStylist = useMemo(
    () => stylists.find((st) => st.id === stylistId) ?? null,
    [stylists, stylistId],
  )

  useEffect(() => {
    setSlots([])
    setSelectedSlot(null)
    setSuccess(null)
    if (!serviceId || !stylistId || !date) return
    setLoading(true)
    setError(null)
    api
      .availability(stylistId, serviceId, date)
      .then((a) => setSlots(a.slots))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [serviceId, stylistId, date])

  // Step 1: clicking a slot selects it (does not book yet).
  function handleSelectSlot(slot: Slot) {
    if (!user) {
      navigate('/login', { state: { from: { pathname: '/' } } })
      return
    }
    setError(null)
    setSuccess(null)
    setSelectedSlot(slot)
  }

  // Step 2: confirm the selected slot to actually book it.
  async function confirmBooking() {
    if (!serviceId || !stylistId || !selectedSlot) return
    setError(null)
    setSuccess(null)
    setBooking(true)
    try {
      await api.book(stylistId, serviceId, selectedSlot.start)
      setSuccess(`Booked for ${fmtTime(selectedSlot.start)}. See "My Appointments".`)
      setSelectedSlot(null)
      // Refresh availability.
      const a = await api.availability(stylistId, serviceId, date)
      setSlots(a.slots)
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setError('That slot was just taken. Please pick another.')
        setSelectedSlot(null)
        const a = await api.availability(stylistId, serviceId, date)
        setSlots(a.slots)
      } else {
        setError((e as Error).message)
      }
    } finally {
      setBooking(false)
    }
  }

  return (
    <div>
      <h1>Book an appointment</h1>
      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}

      <h2>1. Choose a service</h2>
      {services.length === 0 && <p className="muted">No services available.</p>}
      {services.map((s) => (
        <div
          key={s.id}
          className={`card selectable ${serviceId === s.id ? 'selected' : ''}`}
          onClick={() => {
            setServiceId(s.id)
            setStylistId(null)
          }}
        >
          <div className="row">
            <strong>{s.name}</strong>
            <span>${s.price}</span>
          </div>
          <span className="muted">
            {s.duration_min} min{s.category ? ` · ${s.category}` : ''}
          </span>
        </div>
      ))}

      {serviceId && (
        <>
          <h2>2. Choose a stylist</h2>
          {eligibleStylists.length === 0 && (
            <p className="muted">No stylists offer this service.</p>
          )}
          {eligibleStylists.map((st) => (
            <div
              key={st.id}
              className={`card selectable ${stylistId === st.id ? 'selected' : ''}`}
              onClick={() => setStylistId(st.id)}
            >
              <strong>{st.name}</strong>
              {st.bio && <div className="muted">{st.bio}</div>}
            </div>
          ))}
        </>
      )}

      {serviceId && stylistId && (
        <>
          <h2>3. Pick a date &amp; time</h2>
          <label htmlFor="date">Date</label>
          <input
            id="date"
            type="date"
            value={date}
            min={todayISO()}
            onChange={(e) => setDate(e.target.value)}
          />
          {loading && <p className="muted">Loading slots…</p>}
          {!loading && slots.length === 0 && (
            <p className="muted">No open slots for this day.</p>
          )}
          {!loading &&
            groupSlots(slots).map((group) => (
              <div key={group.label} className="slot-group">
                <h3 className="slot-group-label">{group.label}</h3>
                <div className="slots">
                  {group.slots.map((slot) => (
                    <button
                      key={slot.start}
                      className={`slot ${
                        selectedSlot?.start === slot.start ? 'selected' : ''
                      }`}
                      onClick={() => handleSelectSlot(slot)}
                    >
                      {fmtTime(slot.start)}
                    </button>
                  ))}
                </div>
              </div>
            ))}

          {selectedSlot && selectedService && selectedStylist && (
            <div className="card confirm-panel">
              <h3>Confirm your booking</h3>
              <div className="confirm-row">
                <span className="muted">Service</span>
                <strong>{selectedService.name}</strong>
              </div>
              <div className="confirm-row">
                <span className="muted">Stylist</span>
                <strong>{selectedStylist.name}</strong>
              </div>
              <div className="confirm-row">
                <span className="muted">Date</span>
                <strong>{date}</strong>
              </div>
              <div className="confirm-row">
                <span className="muted">Time</span>
                <strong>
                  {fmtTime(selectedSlot.start)} – {fmtTime(selectedSlot.end)}
                </strong>
              </div>
              <div className="confirm-row">
                <span className="muted">Price</span>
                <strong>${selectedService.price}</strong>
              </div>
              <div className="confirm-actions">
                <button onClick={confirmBooking} disabled={booking}>
                  {booking ? 'Booking…' : 'Confirm booking'}
                </button>
                <button
                  className="btn-secondary"
                  onClick={() => setSelectedSlot(null)}
                  disabled={booking}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
