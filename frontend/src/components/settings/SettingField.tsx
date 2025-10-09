import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'

interface SettingFieldProps {
  label: string
  value: string | number
  onChange: (value: string) => void
  description?: string
  type?: 'text' | 'number'
  unit?: string
  disabled?: boolean
}

export function SettingField({ 
  label, 
  value, 
  onChange, 
  description, 
  type = 'text',
  unit,
  disabled = false
}: SettingFieldProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label htmlFor={label} className="text-sm font-medium">
          {label}
        </Label>
        {unit && (
          <Badge variant="outline" className="text-xs">
            {unit}
          </Badge>
        )}
      </div>
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
      <Input
        id={label}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="max-w-md"
      />
    </div>
  )
}
