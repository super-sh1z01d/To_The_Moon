import { Input } from '@/components/ui/input'
import { Search } from 'lucide-react'

interface SettingsSearchProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export function SettingsSearch({ 
  value, 
  onChange, 
  placeholder = 'Search settings...' 
}: SettingsSearchProps) {
  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="pl-9"
      />
    </div>
  )
}
