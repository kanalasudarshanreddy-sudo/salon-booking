// Shared types mirroring the backend API schemas.

export type Role = 'customer' | 'admin'
export type AppointmentStatus = 'booked' | 'cancelled' | 'completed' | 'no_show'

export interface User {
  id: number
  name: string
  email: string
  role: Role
}

export interface Service {
  id: number
  name: string
  duration_min: number
  price: number
  category?: string | null
  active: boolean
}

export interface WorkingHours {
  id: number
  stylist_id: number
  weekday: number
  start: string // HH:MM:SS
  end: string
}

export interface Stylist {
  id: number
  name: string
  bio?: string | null
  active: boolean
  services: Service[]
  working_hours: WorkingHours[]
}

export interface Slot {
  start: string // ISO datetime
  end: string
}

export interface Availability {
  stylist_id: number
  service_id: number
  date: string
  slots: Slot[]
}

export interface Appointment {
  id: number
  customer_id: number
  stylist_id: number
  service_id: number
  start: string
  end: string
  status: AppointmentStatus
  checked_in_at?: string | null
  service?: Service | null
  stylist?: Stylist | null
}

export interface Token {
  access_token: string
  token_type: string
}
