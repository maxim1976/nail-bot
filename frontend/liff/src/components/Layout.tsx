import type { ReactNode } from 'react'

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[#F4EDE5] flex flex-col">
      <header className="px-5 py-4 border-b border-[#241914]/10">
        <h1 className="font-['Bodoni_Moda',serif] text-xl font-semibold text-[#241914]">
          Hualienvibe
        </h1>
      </header>
      <main className="flex-1 px-5 py-6">{children}</main>
    </div>
  )
}
