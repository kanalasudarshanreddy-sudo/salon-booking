import { useEffect, useState } from 'react'
import { api } from '../api'
import type { Appointment } from '../types'

function fmt(iso: string): string {
  return new Date(iso).toLocaleString([], {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export default function HistoryPage() {
  const [appts, setAppts] = useState<Appointment[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    try {
      setAppts(await api.myAppointments())
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  async function cancel(id: number) {
    try {
      await api.cancel(id)
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  if (loading) return <p className="muted">Loading…</p>

  return (
    <div>
      <h1>My Appointments</h1>
      {error && <div className="error">{error}</div>}
      {appts.length === 0 && <p className="muted">No appointments yet.</p>}
      {appts.map((a) => (
        <div className="card" key={a.id}>
          <div className="row">
            <strong>{a.service?.name ?? `Service #${a.service_id}`}</strong>
            <span className={`badge ${a.status}`}>
              {a.status === 'no_show' ? 'no show' : a.status}
            </span>
          </div>
          <div className="muted">
            {a.stylist?.name ?? `Stylist #${a.stylist_id}`} · {fmt(a.start)}
          </div>
          {a.status === 'booked' && (
            <div style={{ marginTop: '0.5rem' }}>
              <button onClick={() => cancel(a.id)}>Cancel</button>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
