import { useEffect, useState } from 'react'
import { fetchServices } from '../api'
import type { Service } from '../types'
import { Layout } from '../components/Layout'

interface Props {
  onSelect: (service: Service) => void
}

export function ServicePicker({ onSelect }: Props) {
  const [services, setServices] = useState<Service[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchServices()
      .then(setServices)
      .catch(() => setError('無法載入服務，請稍後再試'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Layout><p className="text-center mt-10 text-[#241914]/60">載入中...</p></Layout>
  if (error) return <Layout><p className="text-center mt-10 text-red-600">{error}</p></Layout>

  return (
    <Layout>
      <h2 className="font-['Bodoni_Moda',serif] text-2xl mb-6">選擇服務</h2>
      <div className="grid gap-3">
        {services.map(svc => (
          <button
            key={svc.id}
            onClick={() => onSelect(svc)}
            className="w-full text-left bg-white rounded-xl p-4 shadow-sm border border-[#241914]/8 hover:border-[#B86E78] transition-colors"
          >
            <div className="flex justify-between items-start">
              <div>
                <p className="font-semibold text-[#241914]">{svc.name}</p>
                <p className="text-sm text-[#241914]/60 mt-0.5">{svc.name_en}</p>
              </div>
              <div className="text-right shrink-0 ml-3">
                <p className="text-[#A6864F] font-semibold">NT${svc.price}</p>
                <p className="text-xs text-[#241914]/50 mt-0.5">{svc.duration_min}分鐘</p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </Layout>
  )
}
