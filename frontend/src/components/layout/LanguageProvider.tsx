import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { Language, translate } from '@/lib/i18n'

interface LanguageContextValue {
  language: Language
  setLanguage: (language: Language) => void
  t: (key: string, variables?: Record<string, string | number>) => string
}

const LanguageContext = createContext<LanguageContextValue | undefined>(undefined)

interface LanguageProviderProps {
  children: ReactNode
  defaultLanguage?: Language
}

const LOCAL_STORAGE_KEY = 'language'

export function LanguageProvider({ children, defaultLanguage = 'en' }: LanguageProviderProps) {
  const [language, setLanguageState] = useState<Language>(() => {
    const stored = localStorage.getItem(LOCAL_STORAGE_KEY) as Language | null
    return stored ?? defaultLanguage
  })

  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next)
    localStorage.setItem(LOCAL_STORAGE_KEY, next)
  }, [])

  useEffect(() => {
    document.documentElement.setAttribute('lang', language)
  }, [language])

  const t = useCallback(
    (key: string, variables?: Record<string, string | number>) => translate(language, key, variables),
    [language]
  )

  const value = useMemo(
    () => ({
      language,
      setLanguage,
      t,
    }),
    [language, setLanguage, t]
  )

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguageContext() {
  const context = useContext(LanguageContext)
  if (!context) {
    throw new Error('useLanguageContext must be used within LanguageProvider')
  }
  return context
}
