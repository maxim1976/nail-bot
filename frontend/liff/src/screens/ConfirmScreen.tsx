import { useState } from 'react'
import type { Service, Slot, AppointmentOut } from '../types'
import { createAppointment } from '../api'
import { Layout } from '../components/Layout'

interface Props {
  service: Service
  date: string
  slot: Slot
  lineUserId: string
  onSuccess: (appt: AppointmentOut) => void
  onBack: () => void
}

export function ConfirmScreen({ service, date, slot, lineUserId, onSuccess, onBack }: Props) {
  const [name, setName] = useState('')
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const timeLabel = new Date(slot.start).toLocaleTimeString('zh-TW', {
    hour: '2-digit', minute: '2-digit', hour12: false,
  })

  async function submit() {
    if (!name.trim()) { setError('請輸入姓名'); return }
    setLoading(true)
    setError(null)
    try {
      const appt = await createAppointment({
        line_user_id: lineUserId,
        service_id: service.id,
        scheduled_at: slot.start,
        customer_name: name.trim(),
        notes: notes.trim() || undefined,
      })
      onSuccess(appt)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : ''
      setError(msg === 'SLOT_TAKEN' ? '此時段已被預訂，請返回選擇其他時間' : '預約失敗，請稍後再試')
      setLoading(false)
    }
  }

  return (
    <Layout>
      <button onClick={onBack} className="text-[#B86E78] text-sm mb-4">← 返回</button>
      <h2 className="font-['Bodoni_Moda',serif] text-2xl mb-5">確認預約</h2>

      <div className="bg-white rounded-xl p-4 mb-5 space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-[#241914]/60">服務</span>
          <span className="font-semibold">{service.name}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-[#241914]/60">日期</span>
          <span className="font-semibold">{date}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-[#241914]/60">時間</span>
          <span className="font-semibold">{timeLabel}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-[#241914]/60">費用</span>
          <span className="font-semibold text-[#A6864F]">NT${service.price}</span>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1.5">姓名 *</label>
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="請輸入您的姓名"
            className="w-full border border-[#241914]/20 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:border-[#B86E78]"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1.5">備註（可選）</label>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="特殊需求或備注..."
            rows={3}
            className="w-full border border-[#241914]/20 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:border-[#B86E78] resize-none"
          />
        </div>
      </div>

      {error && <p className="mt-3 text-red-600 text-sm">{error}</p>}

      <button
        onClick={submit}
        disabled={loading}
        className="mt-6 w-full bg-[#B86E78] text-white rounded-xl py-3.5 font-semibold disabled:opacity-50 transition-opacity"
      >
        {loading ? '送出中...' : '確認預約'}
      </button>
    </Layout>
  )
}
