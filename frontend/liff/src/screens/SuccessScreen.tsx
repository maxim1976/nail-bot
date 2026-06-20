import type { AppointmentOut } from '../types'
import { Layout } from '../components/Layout'

interface Props {
  appointment: AppointmentOut
}

export function SuccessScreen({ appointment }: Props) {
  const dt = new Date(appointment.scheduled_at)
  const dateStr = dt.toLocaleDateString('zh-TW', { year: 'numeric', month: 'long', day: 'numeric' })
  const timeStr = dt.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', hour12: false })

  return (
    <Layout>
      <div className="flex flex-col items-center text-center mt-10">
        <div className="text-5xl mb-4">✅</div>
        <h2 className="font-['Bodoni_Moda',serif] text-2xl text-[#241914] mb-2">預約成功！</h2>
        <p className="text-[#241914]/60 text-sm mb-6">確認訊息已傳送至您的 LINE</p>
        <div className="bg-white rounded-xl p-5 w-full max-w-sm text-left space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-[#241914]/60">服務</span>
            <span className="font-semibold">{appointment.service_name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#241914]/60">日期</span>
            <span className="font-semibold">{dateStr}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#241914]/60">時間</span>
            <span className="font-semibold">{timeStr}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#241914]/60">姓名</span>
            <span className="font-semibold">{appointment.customer_name}</span>
          </div>
        </div>
        <button
          onClick={() => window.liff?.closeWindow()}
          className="mt-8 bg-[#B86E78] text-white rounded-xl px-8 py-3 font-semibold"
        >
          返回 LINE
        </button>
      </div>
    </Layout>
  )
}
