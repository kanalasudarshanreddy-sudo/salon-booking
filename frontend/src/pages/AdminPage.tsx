import { FormEvent, useEffect, useState } from 'react'
import { api } from '../api'
import type { Appointment, Service, Stylist } from '../types'

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function fmt(iso: string): string {
  return new Date(iso).toLocaleString([], {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export default function AdminPage() {
  const [services, setServices] = useState<Service[]>([])
  const [stylists, setStylists] = useState<Stylist[]>([])
  const [appts, setAppts] = useState<Appointment[]>([])
  const [error, setError] = useState<string | null>(null)

  // New service form.
  const [svcName, setSvcName] = useState('')
  const [svcDuration, setSvcDuration] = useState(30)
  const [svcPrice, setSvcPrice] = useState(30)

  // New stylist form.
  const [styName, setStyName] = useState('')
  const [styBio, setStyBio] = useState('')
  const [styServiceIds, setStyServiceIds] = useState<number[]>([])
  const [styDays, setStyDays] = useState<number[]>([0, 1, 2, 3, 4])
  const [styStart, setStyStart] = useState('09:00')
  const [styEnd, setStyEnd] = useState('17:00')

  async function loadAll() {
    try {
      const [s, st, ap] = await Promise.all([
        api.listServices(),
        api.listStylists(),
        api.allAppointments(),
      ])
      setServices(s)
      setStylists(st)
      setAppts(ap)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  useEffect(() => {
    void loadAll()
  }, [])

  async function addService(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await api.createService({
        name: svcName,
        duration_min: svcDuration,
        price: svcPrice,
      })
      setSvcName('')
      await loadAll()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function addStylist(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await api.createStylist({
        name: styName,
        bio: styBio || undefined,
        service_ids: styServiceIds,
        working_hours: styDays.map((weekday) => ({
          weekday,
          start: `${styStart}:00`,
          end: `${styEnd}:00`,
        })),
      })
      setStyName('')
      setStyBio('')
      setStyServiceIds([])
      await loadAll()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  function toggle<T>(arr: T[], v: T): T[] {
    return arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]
  }

  return (
    <div>
      <h1>Admin</h1>
      {error && <div className="error">{error}</div>}

      <div className="card">
        <h2>Add service</h2>
        <form onSubmit={addService}>
          <label>Name</label>
          <input value={svcName} onChange={(e) => setSvcName(e.target.value)} required />
          <div className="row">
            <div style={{ flex: 1 }}>
              <label>Duration (min)</label>
              <input
                type="number"
                value={svcDuration}
                onChange={(e) => setSvcDuration(Number(e.target.value))}
                min={5}
                required
              />
            </div>
            <div style={{ flex: 1 }}>
              <label>Price ($)</label>
              <input
                type="number"
                value={svcPrice}
                onChange={(e) => setSvcPrice(Number(e.target.value))}
                min={0}
                required
              />
            </div>
          </div>
          <button type="submit">Add service</button>
        </form>
        <ul>
          {services.map((s) => (
            <li key={s.id}>
              {s.name} — {s.duration_min}min — ${s.price}{' '}
              <button
                className="link-btn"
                onClick={async () => {
                  await api.deleteService(s.id)
                  await loadAll()
                }}
              >
                delete
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="card">
        <h2>Add stylist</h2>
        <form onSubmit={addStylist}>
          <label>Name</label>
          <input value={styName} onChange={(e) => setStyName(e.target.value)} required />
          <label>Bio</label>
          <input value={styBio} onChange={(e) => setStyBio(e.target.value)} />

          <label>Services offered</label>
          <div className="row" style={{ flexWrap: 'wrap', justifyContent: 'flex-start' }}>
            {services.map((s) => (
              <label key={s.id} style={{ fontWeight: 400, marginRight: '1rem' }}>
                <input
                  type="checkbox"
                  style={{ width: 'auto', marginRight: 4 }}
                  checked={styServiceIds.includes(s.id)}
                  onChange={() => setStyServiceIds((prev) => toggle(prev, s.id))}
                />
                {s.name}
              </label>
            ))}
          </div>

          <label>Working days</label>
          <div className="row" style={{ flexWrap: 'wrap', justifyContent: 'flex-start' }}>
            {WEEKDAYS.map((d, i) => (
              <label key={i} style={{ fontWeight: 400, marginRight: '0.75rem' }}>
                <input
                  type="checkbox"
                  style={{ width: 'auto', marginRight: 4 }}
                  checked={styDays.includes(i)}
                  onChange={() => setStyDays((prev) => toggle(prev, i))}
                />
                {d}
              </label>
            ))}
          </div>

          <div className="row">
            <div style={{ flex: 1 }}>
              <label>Start</label>
              <input type="time" value={styStart} onChange={(e) => setStyStart(e.target.value)} />
            </div>
            <div style={{ flex: 1 }}>
              <label>End</label>
              <input type="time" value={styEnd} onChange={(e) => setStyEnd(e.target.value)} />
            </div>
          </div>
          <button type="submit">Add stylist</button>
        </form>
        <ul>
          {stylists.map((st) => (
            <li key={st.id}>
              {st.name} ({st.services.map((s) => s.name).join(', ') || 'no services'}){' '}
              <button
                className="link-btn"
                onClick={async () => {
                  await api.deleteStylist(st.id)
                  await loadAll()
                }}
              >
                delete
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="card">
        <h2>All bookings</h2>
        {appts.length === 0 && <p className="muted">No bookings.</p>}
        {appts.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Service</th>
                <th>Stylist</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {appts.map((a) => (
                <tr key={a.id}>
                  <td>{fmt(a.start)}</td>
                  <td>{a.service?.name ?? a.service_id}</td>
                  <td>{a.stylist?.name ?? a.stylist_id}</td>
                  <td>
                    <span className={`badge ${a.status === 'cancelled' ? 'cancelled' : ''}`}>
                      {a.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
