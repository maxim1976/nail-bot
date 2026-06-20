import { useEffect, useState } from 'react'
import { fetchSlots } from '../api'
import type { Service, Slot } from '../types'
import { Layout } from '../components/Layout'

interface Props {
  service: Service
  date: string
  onSelect: (slot: Slot) => void
  onBack: () => void
}

export function TimePicker({ service, date, onSelect, onBack }: Props) {
  const [slots, setSlots] = useState<Slot[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSlots(service.id, date)
      .then(setSlots)
      .finally(() => setLoading(false))
  }, [service.id, date])

  const fmt = (iso: string) =>
    new Date(iso).toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', hour12: false })

  if (loading) return <Layout><p className="text-center mt-10 text-[#241914]/60">載入中...</p></Layout>

  return (
    <Layout>
      <button onClick={onBack} className="text-[#B86E78] text-sm mb-4">← 返回</button>
      <h2 className="font-['Bodoni_Moda',serif] text-2xl mb-2">選擇時間</h2>
      <p className="text-sm text-[#241914]/60 mb-5">{date} · {service.name}</p>
      {slots.length === 0 ? (
        <p className="text-center text-[#241914]/50 mt-10">當天已無可用時段</p>
      ) : (
        <div className="grid grid-cols-3 gap-3">
          {slots.map(slot => (
            <button
              key={slot.start}
              onClick={() => onSelect(slot)}
              className="py-3 bg-white rounded-xl border border-[#241914]/10 hover:border-[#B86E78] hover:bg-[#B86E78]/5 transition-colors font-semibold text-[#241914]"
            >
              {fmt(slot.start)}
            </button>
          ))}
        </div>
      )}
    </Layout>
  )
}
