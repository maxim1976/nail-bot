export interface Service {
  id: string
  name: string
  name_en: string
  name_tl: string
  name_id: string
  name_vi: string
  description: string
  duration_min: number
  price: number
  image_url: string | null
  category: string
  sort_order: number
}

export interface Slot {
  start: string  // ISO datetime string
}

export interface AppointmentIn {
  line_user_id: string
  service_id: string
  scheduled_at: string
  customer_name: string
  notes?: string
}

export interface AppointmentOut {
  id: string
  service_name: string
  scheduled_at: string
  duration_min: number
  status: string
  customer_name: string
  notes?: string
}

export interface PortfolioItem {
  id: string
  title: string
  image_url: string
  service_id: string | null
  service_name: string | null
  service_category: string | null
  sort_order: number
}

export type Screen =
  | 'service'
  | 'date'
  | 'time'
  | 'confirm'
  | 'success'
  | 'gallery'
