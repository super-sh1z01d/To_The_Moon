import { Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from './ThemeToggle'

interface HeaderProps {
  title: string
  onMenuClick?: () => void
  actions?: React.ReactNode
}

export function Header({ title, onMenuClick, actions }: HeaderProps) {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        <div className="mr-4 flex lg:hidden">
          <Button
            variant="ghost"
            size="icon"
            onClick={onMenuClick}
            aria-label="Toggle menu"
          >
            <Menu className="h-5 w-5" />
          </Button>
        </div>
        
        <div className="flex flex-1 items-center justify-end space-x-2">
          {actions}
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}
