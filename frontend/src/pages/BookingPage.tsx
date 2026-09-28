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

export default function BookingPage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [services, setServices] = useState<Service[]>([])
  const [stylists, setStylists] = useState<Stylist[]>([])
  const [serviceId, setServiceId] = useState<number | null>(null)
  const [stylistId, setStylistId] = useState<number | null>(null)
  const [date, setDate] = useState<string>(todayISO())
  const [slots, setSlots] = useState<Slot[]>([])
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

  useEffect(() => {
    setSlots([])
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

  async function handleBook(slot: Slot) {
    if (!user) {
      navigate('/login', { state: { from: { pathname: '/' } } })
      return
    }
    if (!serviceId || !stylistId) return
    setError(null)
    setSuccess(null)
    try {
      await api.book(stylistId, serviceId, slot.start)
      setSuccess(`Booked for ${fmtTime(slot.start)}. See "My Appointments".`)
      // Refresh availability.
      const a = await api.availability(stylistId, serviceId, date)
      setSlots(a.slots)
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setError('That slot was just taken. Please pick another.')
        const a = await api.availability(stylistId, serviceId, date)
        setSlots(a.slots)
      } else {
        setError((e as Error).message)
      }
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
          <div className="slots">
            {slots.map((slot) => (
              <button
                key={slot.start}
                className="slot"
                onClick={() => handleBook(slot)}
              >
                {fmtTime(slot.start)}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
