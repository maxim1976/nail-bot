import { useEffect, useState } from 'react'
import { fetchSlots } from '../api'
import type { Service } from '../types'
import { Layout } from '../components/Layout'

interface Props {
  service: Service
  onSelect: (date: string) => void
  onBack: () => void
}

function addDays(d: Date, n: number): Date {
  const r = new Date(d)
  r.setDate(r.getDate() + n)
  return r
}

function toYMD(d: Date): string {
  return d.toISOString().split('T')[0]
}

export function DatePicker({ service, onSelect, onBack }: Props) {
  const [availableDates, setAvailableDates] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)

  const today = new Date()
  const days: Date[] = Array.from({ length: 30 }, (_, i) => addDays(today, i + 1))

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all(
      days.map(async d => {
        const slots = await fetchSlots(service.id, toYMD(d))
        return { date: toYMD(d), hasSlots: slots.length > 0 }
      })
    ).then(results => {
      if (cancelled) return
      setAvailableDates(new Set(results.filter(r => r.hasSlots).map(r => r.date)))
      setLoading(false)
    })
    return () => { cancelled = true }
  }, [service.id])

  if (loading) return (
    <Layout>
      <p className="text-center mt-10 text-[#241914]/60">載入可用日期中...</p>
    </Layout>
  )

  return (
    <Layout>
      <button onClick={onBack} className="text-[#B86E78] text-sm mb-4">← 返回</button>
      <h2 className="font-['Bodoni_Moda',serif] text-2xl mb-2">選擇日期</h2>
      <p className="text-sm text-[#241914]/60 mb-5">{service.name}</p>
      <div className="grid grid-cols-5 gap-2">
        {days.map(d => {
          const ymd = toYMD(d)
          const available = availableDates.has(ymd)
          const label = d.toLocaleDateString('zh-TW', { month: 'short', day: 'numeric' })
          const weekday = d.toLocaleDateString('zh-TW', { weekday: 'short' })
          return (
            <button
              key={ymd}
              onClick={() => available && onSelect(ymd)}
              disabled={!available}
              className={`flex flex-col items-center py-2 rounded-lg text-xs transition-colors ${
                available
                  ? 'bg-white border border-[#241914]/10 hover:border-[#B86E78] text-[#241914]'
                  : 'bg-[#241914]/5 text-[#241914]/30 cursor-not-allowed'
              }`}
            >
              <span>{weekday}</span>
              <span className="font-semibold mt-0.5">{label.replace('月', '/').replace('日', '')}</span>
            </button>
          )
        })}
      </div>
    </Layout>
  )
}
