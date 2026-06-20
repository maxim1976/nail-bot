import { useEffect, useState } from 'react'
import { fetchPortfolio, fetchServices } from '../api'
import type { PortfolioItem, Service } from '../types'
import { Layout } from '../components/Layout'

interface Props {
  onBook: (service: Service) => void
  onBack: () => void
}

export function GalleryScreen({ onBook, onBack }: Props) {
  const [items, setItems] = useState<PortfolioItem[]>([])
  const [serviceMap, setServiceMap] = useState<Map<string, Service>>(new Map())
  const [activeCategory, setActiveCategory] = useState<string>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    Promise.all([fetchPortfolio(), fetchServices()])
      .then(([portfolio, services]) => {
        setItems(portfolio)
        setServiceMap(new Map(services.map(s => [s.id, s])))
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [])

  const categories = [
    'all',
    ...Array.from(
      new Set(items.filter(i => i.service_category).map(i => i.service_category!))
    ),
  ]

  const visible =
    activeCategory === 'all'
      ? items
      : items.filter(i => i.service_category === activeCategory)

  if (loading) return (
    <Layout>
      <p className="text-center mt-10 text-[#241914]/60">載入中...</p>
    </Layout>
  )

  if (error) return (
    <Layout>
      <p className="text-center mt-10 text-red-400">載入失敗，請返回重試</p>
      <button onClick={onBack} className="block mx-auto mt-4 text-[#B86E78] text-sm">← 返回</button>
    </Layout>
  )

  return (
    <Layout>
      <button onClick={onBack} className="text-[#B86E78] text-sm mb-4">← 返回</button>
      <h2 className="font-['Bodoni_Moda',serif] text-2xl mb-4">作品集</h2>

      {categories.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-2 mb-4 -mx-1 px-1">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`shrink-0 px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                activeCategory === cat
                  ? 'bg-[#B86E78] text-white'
                  : 'bg-white text-[#241914]/60 border border-[#241914]/10'
              }`}
            >
              {cat === 'all' ? '全部' : cat}
            </button>
          ))}
        </div>
      )}

      {visible.length === 0 ? (
        <p className="text-center text-[#241914]/50 mt-10">暫無作品</p>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          {visible.map(item => {
            const service = item.service_id ? serviceMap.get(item.service_id) : undefined
            return (
              <div key={item.id} className="bg-white rounded-xl overflow-hidden shadow-sm border border-[#241914]/8">
                <img
                  src={item.image_url}
                  alt={item.title}
                  className="w-full aspect-square object-cover"
                  loading="lazy"
                />
                <div className="p-2">
                  <p className="text-xs font-semibold text-[#241914] truncate">{item.title}</p>
                  {item.service_name && (
                    <p className="text-xs text-[#241914]/50 mt-0.5 truncate">{item.service_name}</p>
                  )}
                  {service && (
                    <button
                      onClick={() => onBook(service)}
                      className="mt-2 w-full text-xs text-white bg-[#B86E78] hover:bg-[#a05e68] rounded-full py-1.5 transition-colors"
                    >
                      預約此款式
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </Layout>
  )
}
