// Thin fetch wrapper + typed API methods.
// In dev, requests go to /api and are proxied to the backend (see vite.config.ts).
// Override with VITE_API_BASE for production builds.

import type {
  Appointment,
  Availability,
  Service,
  Stylist,
  Token,
  User,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

const TOKEN_KEY = 'salon_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/**
 * FastAPI returns `detail` as either a string (HTTPException) or an array of
 * validation-error objects ({ loc, msg, type }) for 422s. Normalize both into a
 * human-readable string so the UI never renders "[object Object]".
 */
function normalizeDetail(detail: unknown): string | null {
  if (detail == null) return null
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((d) =>
        d && typeof d === 'object' && 'msg' in d
          ? String((d as { msg: unknown }).msg)
          : String(d),
      )
      .filter(Boolean)
    return msgs.length ? msgs.join('; ') : null
  }
  if (typeof detail === 'object' && 'msg' in (detail as object)) {
    return String((detail as { msg: unknown }).msg)
  }
  try {
    return JSON.stringify(detail)
  } catch {
    return null
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = normalizeDetail(data.detail) ?? detail
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  // Auth
  async register(name: string, email: string, password: string): Promise<Token> {
    return request<Token>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password }),
    })
  },
  async login(email: string, password: string): Promise<Token> {
    return request<Token>('/auth/login-json', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  },
  async me(): Promise<User> {
    return request<User>('/auth/me')
  },

  // Services
  async listServices(): Promise<Service[]> {
    return request<Service[]>('/services')
  },
  async createService(data: Partial<Service>): Promise<Service> {
    return request<Service>('/services', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
  async deleteService(id: number): Promise<void> {
    return request<void>(`/services/${id}`, { method: 'DELETE' })
  },

  // Stylists
  async listStylists(): Promise<Stylist[]> {
    return request<Stylist[]>('/stylists')
  },
  async createStylist(data: {
    name: string
    bio?: string
    service_ids: number[]
    working_hours: { weekday: number; start: string; end: string }[]
  }): Promise<Stylist> {
    return request<Stylist>('/stylists', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
  async deleteStylist(id: number): Promise<void> {
    return request<void>(`/stylists/${id}`, { method: 'DELETE' })
  },

  // Availability
  async availability(
    stylistId: number,
    serviceId: number,
    date: string,
  ): Promise<Availability> {
    const q = new URLSearchParams({
      stylist_id: String(stylistId),
      service_id: String(serviceId),
      date,
    })
    return request<Availability>(`/availability?${q.toString()}`)
  },

  // Appointments
  async book(
    stylistId: number,
    serviceId: number,
    start: string,
  ): Promise<Appointment> {
    return request<Appointment>('/appointments', {
      method: 'POST',
      body: JSON.stringify({
        stylist_id: stylistId,
        service_id: serviceId,
        start,
      }),
    })
  },
  async myAppointments(): Promise<Appointment[]> {
    return request<Appointment[]>('/appointments/me')
  },
  async allAppointments(): Promise<Appointment[]> {
    return request<Appointment[]>('/appointments')
  },
  async cancel(id: number): Promise<Appointment> {
    return request<Appointment>(`/appointments/${id}/cancel`, {
      method: 'PATCH',
    })
  },
  async checkIn(id: number): Promise<Appointment> {
    return request<Appointment>(`/appointments/${id}/check-in`, {
      method: 'PATCH',
    })
  },
  async undoCheckIn(id: number): Promise<Appointment> {
    return request<Appointment>(`/appointments/${id}/undo-check-in`, {
      method: 'PATCH',
    })
  },
}
