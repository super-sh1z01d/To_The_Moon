import { NavLink } from 'react-router-dom'
import { Home, Settings, FileText } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useLanguage } from '@/hooks/useLanguage'

const navigation = [
  { name: 'Dashboard', href: '/app/', icon: Home },
  { name: 'API Docs', href: '/app/api-docs', icon: FileText },
  { name: 'Settings', href: '/app/settings', icon: Settings },
  { name: 'Logs', href: '/app/logs', icon: FileText },
]

export function MobileNav() {
  const { t } = useLanguage()

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t bg-background md:hidden">
      <div className="flex items-center justify-around">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              cn(
                'flex flex-col items-center space-y-1 px-3 py-2 text-xs font-medium transition-colors',
                isActive
                  ? 'text-primary'
                  : 'text-muted-foreground'
              )
            }
          >
            <item.icon className="h-5 w-5" />
            <span>{t(item.name)}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
