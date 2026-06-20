import { useEffect, useState } from 'react'
import type { AppointmentOut, Screen, Service, Slot } from './types'
import { ServicePicker } from './screens/ServicePicker'
import { DatePicker } from './screens/DatePicker'
import { TimePicker } from './screens/TimePicker'
import { ConfirmScreen } from './screens/ConfirmScreen'
import { SuccessScreen } from './screens/SuccessScreen'
import { GalleryScreen } from './screens/GalleryScreen'

declare global {
  interface Window {
    liff: {
      init: (config: { liffId: string }) => Promise<void>
      getProfile: () => Promise<{ userId: string; displayName: string }>
      closeWindow: () => void
      isInClient: () => boolean
    }
  }
}

const LIFF_ID = import.meta.env.VITE_LIFF_ID ?? ''

export function App() {
  const [screen, setScreen] = useState<Screen>('service')
  const [lineUserId, setLineUserId] = useState<string>('')
  const [ready, setReady] = useState(false)
  const [initError, setInitError] = useState<string | null>(null)

  const [selectedService, setSelectedService] = useState<Service | null>(null)
  const [selectedDate, setSelectedDate] = useState<string>('')
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null)
  const [appointment, setAppointment] = useState<AppointmentOut | null>(null)

  useEffect(() => {
    if (!LIFF_ID) {
      setLineUserId('U_dev_user')
      setReady(true)
      return
    }
    window.liff
      .init({ liffId: LIFF_ID })
      .then(() => window.liff.getProfile())
      .then(p => {
        setLineUserId(p.userId)
        setReady(true)
      })
      .catch(() => setInitError('無法初始化 LINE，請在 LINE 中開啟此頁面'))
  }, [])

  if (initError) return (
    <div className="flex items-center justify-center min-h-screen bg-[#F4EDE5]">
      <p className="text-red-600 text-center px-5">{initError}</p>
    </div>
  )

  if (!ready) return (
    <div className="flex items-center justify-center min-h-screen bg-[#F4EDE5]">
      <p className="text-[#241914]/50">Loading...</p>
    </div>
  )

  if (screen === 'service') return (
    <ServicePicker
      onSelect={svc => { setSelectedService(svc); setScreen('date') }}
      onGallery={() => setScreen('gallery')}
    />
  )

  if (screen === 'gallery') return (
    <GalleryScreen
      onBook={svc => { setSelectedService(svc); setScreen('date') }}
      onBack={() => setScreen('service')}
    />
  )

  if (screen === 'date' && selectedService) return (
    <DatePicker
      service={selectedService}
      onSelect={d => { setSelectedDate(d); setScreen('time') }}
      onBack={() => setScreen('service')}
    />
  )

  if (screen === 'time' && selectedService) return (
    <TimePicker
      service={selectedService}
      date={selectedDate}
      onSelect={slot => { setSelectedSlot(slot); setScreen('confirm') }}
      onBack={() => setScreen('date')}
    />
  )

  if (screen === 'confirm' && selectedService && selectedSlot) return (
    <ConfirmScreen
      service={selectedService}
      date={selectedDate}
      slot={selectedSlot}
      lineUserId={lineUserId}
      onSuccess={appt => { setAppointment(appt); setScreen('success') }}
      onBack={() => setScreen('time')}
    />
  )

  if (screen === 'success' && appointment) return (
    <SuccessScreen appointment={appointment} />
  )

  return null
}
