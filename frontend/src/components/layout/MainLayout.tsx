import { useState } from 'react'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { MobileNav } from './MobileNav'

interface MainLayoutProps {
  children: React.ReactNode
  title?: string
  actions?: React.ReactNode
}

export function MainLayout({ children, title = 'To The Moon', actions }: MainLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex min-h-screen">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      
      <div className="flex flex-1 flex-col">
        <Header
          title={title}
          onMenuClick={() => setSidebarOpen(true)}
          actions={actions}
        />
        
        <main className="flex-1 overflow-y-auto p-4 pb-20 lg:p-6 lg:pb-6">
          <div className="mx-auto max-w-7xl">
            {children}
          </div>
        </main>
        
        <MobileNav />
      </div>
    </div>
  )
}
