import type { AppointmentIn, AppointmentOut, PortfolioItem, Service, Slot } from './types'

const BASE = import.meta.env.VITE_API_BASE ?? ''

export async function fetchServices(): Promise<Service[]> {
  const r = await fetch(`${BASE}/api/services`)
  if (!r.ok) throw new Error('Failed to load services')
  return r.json()
}

export async function fetchSlots(serviceId: string, date: string): Promise<Slot[]> {
  const r = await fetch(`${BASE}/api/slots?service_id=${serviceId}&date=${date}`)
  if (!r.ok) throw new Error('Failed to load slots')
  return r.json()
}

export async function createAppointment(body: AppointmentIn): Promise<AppointmentOut> {
  const r = await fetch(`${BASE}/api/appointments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (r.status === 409) throw new Error('SLOT_TAKEN')
  if (!r.ok) throw new Error('Failed to create appointment')
  return r.json()
}

export async function fetchPortfolio(): Promise<PortfolioItem[]> {
  const r = await fetch(`${BASE}/api/portfolio`)
  if (!r.ok) throw new Error('Failed to load portfolio')
  return r.json()
}
