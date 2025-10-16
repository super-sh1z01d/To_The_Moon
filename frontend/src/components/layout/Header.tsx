import { Menu } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from './ThemeToggle'
import { LanguageToggle } from './LanguageToggle'
import { useLanguage } from '@/hooks/useLanguage'
import { useAuth } from '@/hooks/useAuth'
import { useModal } from '@/contexts/ModalContext'

interface HeaderProps {
  title: string
  onMenuClick?: () => void
}

export function Header({ title, onMenuClick }: HeaderProps) {
  const { t } = useLanguage()
  const { isAuthenticated, logout } = useAuth()
  const { openModal } = useModal()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-50 w-full bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-12 items-center px-4 border-b">
        <div className="mr-4 flex lg:hidden">
          <Button
            variant="ghost"
            size="icon"
            onClick={onMenuClick}
            aria-label={t('Toggle menu')}
          >
            <Menu className="h-5 w-5" />
          </Button>
        </div>

        <div className="flex flex-1 items-center justify-between">
          <h1 className="text-base font-semibold lg:hidden">{title}</h1>

          <div className="flex items-center space-x-2 ml-auto">
            {isAuthenticated ? (
              <Button variant="outline" onClick={handleLogout}>{t('Logout')}</Button>
            ) : (
              <>
                <Button variant="ghost" onClick={() => openModal('login')}>{t('Login')}</Button>
                <Button onClick={() => openModal('register')}>{t('Register')}</Button>
              </>
            )}
            <LanguageToggle />
            <ThemeToggle />
          </div>
        </div>
      </div>
    </header>
  )
}
