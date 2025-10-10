import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useLanguage } from '@/hooks/useLanguage'
import type { Language } from '@/lib/i18n'

export function LanguageToggle() {
  const { language, setLanguage, t } = useLanguage()

  const handleChange = (value: string) => {
    setLanguage(value as Language)
  }

  return (
    <Select value={language} onValueChange={handleChange}>
      <SelectTrigger className="w-[130px]" aria-label={t('Language')}>
        <SelectValue placeholder={t('Language')} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="en">{t('English')}</SelectItem>
        <SelectItem value="ru">{t('Russian')}</SelectItem>
      </SelectContent>
    </Select>
  )
}
