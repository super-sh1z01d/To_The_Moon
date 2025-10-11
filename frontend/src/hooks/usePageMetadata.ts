import { useEffect } from 'react'
import { useLanguage } from './useLanguage'

type MetaContent = {
  title: string
  description: string
  keywords?: string[]
}

export interface PageMetadataConfig {
  en: MetaContent
  ru: MetaContent
  canonical?: string
  image?: string
  ogType?: string
  twitterCard?: string
  siteName?: string
}

function upsertMeta(attribute: 'name' | 'property', key: string, value: string | undefined) {
  if (!value || value.length === 0) {
    const existing = document.head.querySelector(`meta[${attribute}="${key}"]`)
    if (existing) existing.remove()
    return
  }

  let meta = document.head.querySelector(`meta[${attribute}="${key}"]`) as HTMLMetaElement | null
  if (!meta) {
    meta = document.createElement('meta')
    meta.setAttribute(attribute, key)
    document.head.appendChild(meta)
  }
  meta.setAttribute('content', value)
}

function upsertLink(rel: string, href: string) {
  let link = document.head.querySelector(`link[rel="${rel}"]`) as HTMLLinkElement | null
  if (!link) {
    link = document.createElement('link')
    link.setAttribute('rel', rel)
    document.head.appendChild(link)
  }
  link.setAttribute('href', href)
}

const FALLBACK_ORIGIN = 'https://tothemoon.sh1z01d.ru'

export function usePageMetadata(config: PageMetadataConfig) {
  const { language } = useLanguage()

  useEffect(() => {
    const meta = language === 'ru' ? config.ru : config.en
    const locale = language === 'ru' ? 'ru_RU' : 'en_US'
    const origin = typeof window !== 'undefined' ? window.location.origin : FALLBACK_ORIGIN
    const canonical = config.canonical ?? (typeof window !== 'undefined' ? window.location.href : origin)

    document.title = meta.title

    upsertMeta('name', 'description', meta.description)
    upsertMeta('name', 'keywords', meta.keywords?.join(', '))
    upsertMeta('property', 'og:title', meta.title)
    upsertMeta('property', 'og:description', meta.description)
    upsertMeta('property', 'og:locale', locale)
    upsertMeta('property', 'og:site_name', config.siteName ?? 'To The Moon')
    upsertMeta('property', 'og:type', config.ogType ?? 'website')
    upsertMeta('property', 'og:url', canonical)

    upsertMeta('name', 'twitter:title', meta.title)
    upsertMeta('name', 'twitter:description', meta.description)
    upsertMeta('name', 'twitter:card', config.twitterCard ?? 'summary_large_image')

    if (config.image) {
      upsertMeta('property', 'og:image', config.image)
      upsertMeta('name', 'twitter:image', config.image)
    }

    upsertLink('canonical', canonical)
  }, [language, config])
}
