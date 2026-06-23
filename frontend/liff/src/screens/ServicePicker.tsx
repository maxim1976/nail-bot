import { useEffect, useState } from 'react'
import { fetchServices } from '../api'
import type { Service } from '../types'
import { Layout } from '../components/Layout'

interface Props {
  onSelect: (service: Service) => void
  onGallery?: () => void
}

const FALLBACK_COLORS: Record<string, string> = {
  gel:      'from-pink-300 to-rose-400',
  art:      'from-violet-300 to-purple-400',
  removal:  'from-slate-300 to-gray-400',
  care:     'from-amber-200 to-yellow-300',
  pedicure: 'from-teal-300 to-cyan-400',
  general:  'from-rose-200 to-pink-300',
}

function ServiceCard({ svc, onSelect }: { svc: Service; onSelect: (s: Service) => void }) {
  const [imgError, setImgError] = useState(false)
  const gradient = FALLBACK_COLORS[svc.category] ?? FALLBACK_COLORS.general

  return (
    <button
      onClick={() => onSelect(svc)}
      className="w-full text-left rounded-2xl overflow-hidden shadow-sm border border-black/5 hover:shadow-md transition-shadow active:scale-[0.98] transition-transform"
    >
      {/* Image / colour header */}
      <div className="relative h-40 overflow-hidden">
        {svc.image_url && !imgError ? (
          <img
            src={svc.image_url}
            alt={svc.name}
            onError={() => setImgError(true)}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className={`w-full h-full bg-gradient-to-br ${gradient}`} />
        )}
        {/* Bottom gradient overlay with Chinese name */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/10 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-3">
          <p className="text-white font-semibold text-lg leading-tight drop-shadow">{svc.name}</p>
        </div>
      </div>

      {/* Info row */}
      <div className="bg-white px-4 py-3 flex items-center justify-between">
        <p className="text-sm text-[#241914]/50">{svc.name_en}</p>
        <div className="text-right shrink-0 ml-3">
          <p className="text-[#A6864F] font-semibold text-sm">NT${svc.price}</p>
          <p className="text-xs text-[#241914]/40">{svc.duration_min} 分鐘</p>
        </div>
      </div>
    </button>
  )
}

export function ServicePicker({ onSelect, onGallery }: Props) {
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
      <div className="flex justify-between items-center mb-5">
        <h2 className="font-['Bodoni_Moda',serif] text-2xl">選擇服務</h2>
        {onGallery && (
          <button onClick={onGallery} className="text-sm text-[#B86E78] font-medium">
            作品集 →
          </button>
        )}
      </div>
      <div className="grid gap-4">
        {services.map(svc => (
          <ServiceCard key={svc.id} svc={svc} onSelect={onSelect} />
        ))}
      </div>
    </Layout>
  )
}
