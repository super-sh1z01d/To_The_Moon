import { useMemo } from 'react'
import {
  ArrowRight,
  BarChart3,
  Bot,
  Compass,
  Plug,
  Rocket,
  ShieldCheck,
  Sparkles,
  Target,
  Zap,
  Send,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useLanguage } from '@/hooks/useLanguage'
import { useTokenStats } from '@/hooks/useTokenStats'
import { useTokens } from '@/hooks/useTokens'
import { cn, formatCurrency } from '@/lib/utils'

type Lang = 'en' | 'ru'

const ACTIVE_FILTER = { status: 'active', limit: 10, sort: 'score_desc' as const }
const MONITORING_FILTER = { status: 'monitoring', limit: 50, sort: 'score_desc' as const }
const ONE_DAY = 24 * 60 * 60 * 1000

const TEXT = {
  en: {
    heroTitle: 'Arbitrage Solana memecoins without blind spots',
    heroSubtitle: 'Pump.fun → External DEX → Ready-made bundles for your bot',
    ctaLogin: 'Sign in',
    ctaRegister: 'Create account',
    brand: 'To The Moon',
    betaLabel: 'Beta access',
    stats: {
      fresh: 'New mints (24h)',
      activated: 'Activated (24h)',
      pools: 'Pools created (24h)',
      liquidity: 'Liquidity added (24h)',
      totalTokens: 'Tokens in system',
    },
    valueTitle: 'Why traders choose To The Moon',
    valueCards: [
      {
        title: 'Catch the launch',
        description: 'We watch Raydium, Meteora, Orca and other DEX the moment a Pump.fun token gets its first pool.',
      },
      {
        title: 'Less competition',
        description: 'Be first on fresh meme pairs before volume and slippage explode with whales.',
      },
      {
        title: 'Bot-ready data',
        description: 'Export configs for NotArb and SolanaMevBot or plug straight into the REST API.',
      },
    ],
    pipelineTitle: 'How it works',
    pipelineSteps: [
      { title: 'Pump.fun mint detected', description: 'Every new token launch is tracked instantly.' },
      { title: 'External pools appear', description: 'We monitor Raydium, Meteora, Orca and more for the first liquidity.' },
      { title: 'Score calculation', description: 'Liquidity, volume, freshness and orderflow roll into a transparent score.' },
      { title: 'Bundles for arbitrage', description: 'Copy ready-made pool lists for bots or act manually in one click.' },
    ],
    liveTitle: 'Live market pulse',
    liveSubtitle: 'Real-time stats for the last 24 hours',
    liveTable: {
      token: 'Token',
      score: 'Score',
      pools: 'Pools',
      liquidity: 'Liquidity',
      empty: 'No standout tokens right now — data refreshes live.',
    },
    liveSummary: {
      minted: 'New mints (24h)',
      activated: 'Activated (24h)',
      pools: 'Pools created (24h)',
      liquidity: 'Liquidity added (24h)',
    },
    liveAssist: 'Scores refresh live using Pump.fun launches and external DEX liquidity.',
    advantagesTitle: 'Built for professional arbitrageurs',
    advantages: [
      {
        title: 'Hardcore metrics',
        description: 'The score blends volume, liquidity, freshness and orderflow — no “sample” dashboards.',
      },
      {
        title: 'Full DEX coverage',
        description: 'Raydium AMM/CPMM/CLMM, Meteora DLMM/DAMM v2, Orca and more on the roadmap.',
      },
      {
        title: 'Beta is free',
        description: 'Join the Telegram community, propose features and grab the edge while it is open beta.',
      },
    ],
    integrationsTitle: 'Integrations & API',
    integrations: [
      {
        title: 'REST API',
        description: 'Plug token feeds and pools directly into your execution stack.',
      },
      {
        title: 'NotArb & SolanaMevBot ready',
        description: 'Download fresh markets.json configs with pool bundles in one click.',
      },
      {
        title: 'Coming soon',
        description: 'Webhooks, streaming updates and on-chain alerts are on the roadmap.',
      },
    ],
    howToTitle: 'How to get started',
    steps: [
      { title: 'Create an account', description: 'Free beta access, no credit card required.' },
      { title: 'Connect your bot', description: 'Use our configs or REST API to bootstrap routes.' },
      { title: 'Track fresh pools', description: 'Receive live updates and execute before the crowd.' },
    ],
    subscribe: {
      title: 'Ready to trade on fresh pools?',
      description: 'Jump into the dashboard and start scanning new liquidity routes in seconds.',
      button: 'Open dashboard',
    },
    communityTitle: 'Community & roadmap',
    timeline: [
      { period: 'Q4 2025', label: 'Alerts & webhooks for fresh pools' },
      { period: 'Q1 2026', label: 'Premium features & advanced analytics' },
    ],
    footer: {
      beta: 'The service is in open beta and completely free.',
      login: 'Sign in',
      register: 'Create account',
    },
    buttons: {
      seeDocs: 'View documentation',
    },
  },
  ru: {
    heroTitle: 'Арбитраж мемкоинов в Solana без слепых зон',
    heroSubtitle: 'Pump.fun → Внешние DEX → Готовые связки для бота',
    ctaLogin: 'Войти',
    ctaRegister: 'Зарегистрироваться',
    brand: 'To The Moon',
    betaLabel: 'Открытая бета',
    stats: {
      fresh: 'Новые минты (24ч)',
      activated: 'Активировано (24ч)',
      pools: 'Создано пулов (24ч)',
      liquidity: 'Ликвидность (24ч)',
      totalTokens: 'Токенов в системе',
    },
    valueTitle: 'Зачем это нужно арбитражникам',
    valueCards: [
      {
        title: 'Поймай старт',
        description: 'Следим за первыми пулами на Raydium, Meteora, Orca и других DEX сразу после Pump.fun.',
      },
      {
        title: 'Меньше конкурентов',
        description: 'Выходи на свежие пары до того, как туда заходят крупные игроки.',
      },
      {
        title: 'Готовые данные',
        description: 'Выгрузка конфигов для NotArb и SolanaMevBot + открытый REST API.',
      },
    ],
    pipelineTitle: 'Как работает сервис',
    pipelineSteps: [
      { title: 'Находим новый mint на Pump.fun', description: 'Фиксируем каждый запуск токена мгновенно.' },
      { title: 'Отслеживаем пулы на DEX', description: 'Raydium, Meteora, Orca — даём сигнал при появлении ликвидности.' },
      { title: 'Считаем score', description: 'Ликвидность, объём, свежесть, ордерфлоу — всё в одном показателе.' },
      { title: 'Готовые связки', description: 'Копируй пул-листы в бота или работай вручную первым.' },
    ],
    liveTitle: 'Пульс рынка в реальном времени',
    liveSubtitle: 'Актуальные показатели за последние 24 часа',
    liveTable: {
      token: 'Токен',
      score: 'Score',
      pools: 'Пулы',
      liquidity: 'Ликвидность',
      empty: 'Пока без ярких токенов — данные обновляются в онлайне.',
    },
    liveSummary: {
      minted: 'Новые минты (24ч)',
      activated: 'Перешли в активные (24ч)',
      pools: 'Создано пулов (24ч)',
      liquidity: 'Добавленная ликвидность (24ч)',
    },
    liveAssist: 'Скоры обновляются в реальном времени по потокам Pump.fun и внешних DEX.',
    advantagesTitle: 'Преимущества для арбитражников',
    advantages: [
      {
        title: 'Hardcore-метрики',
        description: 'Score — это сочетание объёма, ликвидности, свежести и дисбаланса ордеров.',
      },
      {
        title: 'Поддержка топовых DEX',
        description: 'Raydium AMM/CPMM/CLMM, Meteora DLMM/DAMM v2, Orca — расширяем охват постоянно.',
      },
      {
        title: 'Бета бесплатно',
        description: 'Присоединяйся к Telegram и предлагай фичи, пока сервис в открытой бете.',
      },
    ],
    integrationsTitle: 'Интеграции и API',
    integrations: [
      {
        title: 'REST API',
        description: 'Подключай фиды токенов и пулов напрямую в свою инфраструктуру.',
      },
      {
        title: 'Готово для NotArb и SolanaMevBot',
        description: 'Скачай актуальный markets.json с готовыми пулами.',
      },
      {
        title: 'Скоро',
        description: 'Webhooks, стриминг и алерты уже в дорожной карте.',
      },
    ],
    howToTitle: 'Как начать',
    steps: [
      { title: 'Создай аккаунт', description: 'Доступ к бете бесплатный, карта не нужна.' },
      { title: 'Подключи бота', description: 'Используй наши конфиги или REST API для маршрутов.' },
      { title: 'Лови свежие пулы', description: 'Получай апдейты и заходи раньше остальных.' },
    ],
    subscribe: {
      title: 'Готов к арбитражу свежих пулов?',
      description: 'Открой дашборд и начинай отслеживать новые маршруты за пару кликов.',
      button: 'Перейти к дашборду',
    },
    communityTitle: 'Комьюнити и дорожная карта',
    timeline: [
      { period: 'Q4 2025', label: 'Алерты и webhooks по свежим пулам' },
      { period: 'Q1 2026', label: 'Premium-возможности и расширенная аналитика' },
    ],
    footer: {
      beta: 'Сервис в открытой бете и полностью бесплатен.',
      login: 'Войти',
      register: 'Зарегистрироваться',
    },
    buttons: {
      seeDocs: 'Перейти к документации',
    },
  },
} satisfies Record<Lang, any>

function formatInteger(value: number | undefined) {
  if (value === undefined || Number.isNaN(value)) {
    return '—'
  }
  return value.toLocaleString()
}

function LanguageSwitch({ language, onSelect }: { language: Lang; onSelect: (lang: Lang) => void }) {
  const options: Array<{ value: Lang; label: string }> = [
    { value: 'en', label: 'EN' },
    { value: 'ru', label: 'RU' },
  ]

  return (
    <div
      className="inline-flex items-center gap-1 rounded-full border border-muted/40 bg-background/80 p-1 shadow-sm backdrop-blur"
      aria-label="Language switcher"
    >
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onSelect(option.value)}
          className={cn(
            'rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide transition-colors',
            language === option.value
              ? 'bg-primary text-primary-foreground shadow'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

export default function Landing() {
  const { language, setLanguage } = useLanguage()
  const lang: Lang = language === 'ru' ? 'ru' : 'en'
  const copy = TEXT[lang]

  const { data: stats } = useTokenStats()
  const { data: activeTokens } = useTokens(ACTIVE_FILTER)
  const { data: monitoringTokens } = useTokens(MONITORING_FILTER)

  const {
    mintedCount,
    activatedCount,
    totalPools24h,
    totalLiquidity24h,
    topTokens,
  } = useMemo(() => {
    const now = Date.now()
    const active = activeTokens?.items ?? []
    const monitoring = monitoringTokens?.items ?? []
    const indexed = new Map<string, (typeof active)[number]>()

    for (const token of [...active, ...monitoring]) {
      if (token?.mint_address && !indexed.has(token.mint_address)) {
        indexed.set(token.mint_address, token)
      }
    }

    const combined = Array.from(indexed.values())
    const top = active.slice(0, 6)

    const fresh = combined.filter((token) => {
      if (!token.created_at) return false
      const created = Date.parse(token.created_at)
      if (Number.isNaN(created)) return false
      return now - created <= ONE_DAY
    })

    const activatedFresh = fresh.filter((token) => token.status === 'active')
    const totalLiquidity = fresh.reduce((sum, token) => {
      const value = Number(token.liquidity_usd)
      if (!Number.isFinite(value) || value <= 0) {
        return sum
      }
      return sum + value
    }, 0)

    const poolsCount = fresh.reduce((sum, token) => sum + (token.pools?.length ?? 0), 0)

    return {
      mintedCount: fresh.length,
      activatedCount: activatedFresh.length,
      totalPools24h: poolsCount,
      totalLiquidity24h: totalLiquidity,
      topTokens: top,
    }
  }, [activeTokens, monitoringTokens])

  const heroPreview = topTokens.slice(0, 3)

  const heroStats = [
    {
      label: copy.stats.fresh,
      value: formatInteger(mintedCount),
    },
    {
      label: copy.stats.activated,
      value: formatInteger(activatedCount),
    },
    {
      label: copy.stats.pools,
      value: formatInteger(totalPools24h),
    },
    {
      label: copy.stats.liquidity,
      value: totalLiquidity24h > 0 ? formatCurrency(totalLiquidity24h) : '—',
    },
  ]

  const pulseStats = [
    {
      label: copy.liveSummary.minted,
      value: formatInteger(mintedCount),
    },
    {
      label: copy.liveSummary.activated,
      value: formatInteger(activatedCount),
    },
    {
      label: copy.liveSummary.pools,
      value: formatInteger(totalPools24h),
    },
    {
      label: copy.liveSummary.liquidity,
      value: totalLiquidity24h > 0 ? formatCurrency(totalLiquidity24h) : '—',
    },
  ]

  return (
    <div className="min-h-screen bg-background text-foreground">
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/15 via-background to-background" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(123,97,255,0.25),_transparent_60%)]" />
        <div className="pointer-events-none absolute inset-x-0 top-1/3 h-[480px] -translate-y-1/2 bg-[radial-gradient(80%_60%_at_50%_50%,rgba(34,197,94,0.12),transparent)] blur-3xl" />
        <div className="pointer-events-none absolute -left-32 bottom-0 h-72 w-72 rounded-full bg-primary/10 blur-3xl" />
        <div className="pointer-events-none absolute -right-24 top-10 h-60 w-60 rounded-full bg-secondary/20 blur-3xl" />
        <div className="pointer-events-none absolute inset-x-0 -bottom-16 h-64 bg-[radial-gradient(70%_70%_at_50%_50%,rgba(59,130,246,0.08),transparent)] blur-3xl" />
        <div className="relative mx-auto flex max-w-6xl flex-col gap-12 px-4 pb-20 pt-24 lg:px-8 lg:pt-32">
          <div className="flex flex-col gap-10 lg:flex-row lg:items-start">
            <div className="flex-1 space-y-8">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-wrap items-center gap-3 text-xs font-semibold uppercase tracking-wide">
                  <span className="inline-flex items-center gap-2 rounded-full border border-primary/40 bg-primary/10 px-3 py-1 text-primary">
                    <Sparkles className="h-3.5 w-3.5" />
                    {copy.betaLabel}
                  </span>
                  <span className="inline-flex items-center rounded-full border border-muted/40 bg-background/70 px-3 py-1 text-xs text-foreground shadow-sm">
                    {copy.brand}
                  </span>
                </div>
                <LanguageSwitch language={lang} onSelect={(value) => setLanguage(value)} />
              </div>
              <h1 className="text-4xl font-bold leading-tight tracking-tight md:text-5xl lg:text-6xl">
                {copy.heroTitle}
              </h1>
              <p className="max-w-2xl text-lg text-muted-foreground md:text-xl">
                {copy.heroSubtitle}
              </p>
              <div className="flex flex-wrap gap-3">
                <Button size="lg" asChild>
                  <a className="flex items-center whitespace-nowrap" href="/app/">
                    {copy.ctaLogin}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </a>
                </Button>
                <Button size="lg" variant="outline" asChild>
                  <a className="whitespace-nowrap" href="/app/">
                    {copy.ctaRegister}
                  </a>
                </Button>
              </div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {heroStats.map((stat) => (
                  <div
                    key={stat.label}
                    className="rounded-xl border border-primary/20 bg-background/70 p-4 shadow-sm backdrop-blur transition hover:border-primary/30 hover:shadow-lg"
                  >
                    <div className="text-2xl font-semibold text-foreground">{stat.value}</div>
                    <div className="text-sm text-muted-foreground">{stat.label}</div>
                  </div>
                ))}
              </div>
              <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {copy.stats.totalTokens}:{' '}
                <span className="text-foreground">{formatInteger(stats?.total)}</span>
              </div>
            </div>
            <div className="flex-1">
              <div className="rounded-3xl border border-primary/20 bg-background/80 p-6 shadow-xl backdrop-blur">
                <div className="mb-6 flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-primary">{copy.liveTitle}</div>
                    <p className="text-xs text-muted-foreground">{copy.liveSubtitle}</p>
                  </div>
                  <Sparkles className="h-6 w-6 text-primary" />
                </div>
                <div className="overflow-hidden rounded-2xl border border-muted/40">
                  <div className="grid grid-cols-[minmax(0,2fr)_auto_auto_auto] bg-muted/50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    <span>{copy.liveTable.token}</span>
                    <span className="text-right">{copy.liveTable.score}</span>
                    <span className="text-right">{copy.liveTable.pools}</span>
                    <span className="text-right">{copy.liveTable.liquidity}</span>
                  </div>
                  {heroPreview.length > 0 ? (
                    heroPreview.map((token) => (
                      <div
                        key={token.mint_address}
                        className="grid grid-cols-[minmax(0,2fr)_auto_auto_auto] items-center px-4 py-3 text-sm transition hover:bg-muted/30"
                      >
                        <div>
                          <div className="font-semibold">
                            {token.symbol || token.name || token.mint_address.slice(0, 6)}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {token.mint_address.slice(0, 4)}…{token.mint_address.slice(-4)}
                          </div>
                        </div>
                        <div className="text-right font-semibold text-primary">
                          {token.score?.toFixed(3)}
                        </div>
                        <div className="text-right text-sm text-muted-foreground">
                          {token.pools?.length ?? 0}
                        </div>
                        <div className="text-right text-sm font-semibold text-foreground">
                          {formatCurrency(token.liquidity_usd)}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="px-4 py-6 text-sm text-muted-foreground">
                      {copy.liveTable.empty}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="relative mx-auto max-w-5xl px-4 py-16 lg:px-8">
        <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(60%_60%_at_50%_50%,rgba(59,130,246,0.12),transparent)]" />
        <div className="mb-10 text-center">
          <h2 className="text-3xl font-bold lg:text-4xl">{copy.valueTitle}</h2>
        </div>
        <div className="grid gap-6 md:grid-cols-3">
          {copy.valueCards.map((card: { title: string; description: string }, index: number) => {
            const Icon = [Rocket, Zap, Plug][index] ?? Rocket
            return (
              <div
                key={card.title}
                className="group rounded-xl border border-muted bg-card/60 p-6 shadow-sm transition hover:border-primary hover:shadow-lg"
              >
                <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <Icon className="h-6 w-6" />
                </div>
                <h3 className="text-xl font-semibold">{card.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{card.description}</p>
              </div>
            )
          })}
        </div>
      </section>

      <section className="bg-muted/40 py-16">
        <div className="mx-auto max-w-5xl px-4 lg:px-8">
          <h2 className="mb-10 text-center text-3xl font-bold lg:text-4xl">{copy.pipelineTitle}</h2>
          <div className="grid gap-8 md:grid-cols-2">
            {copy.pipelineSteps.map(
              (step: { title: string; description: string }, index: number) => (
                <div key={step.title} className="relative rounded-xl border border-muted bg-background p-6">
                  <div className="absolute -top-4 left-6 flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground shadow">
                    {index + 1}
                  </div>
                  <h3 className="mt-4 text-lg font-semibold">{step.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{step.description}</p>
                </div>
              )
            )}
          </div>
        </div>
      </section>

      <section className="relative mx-auto max-w-6xl px-4 py-20 lg:px-8">
        <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(70%_70%_at_50%_50%,rgba(34,197,94,0.08),transparent)]" />
        <div className="grid gap-12 lg:grid-cols-[3fr_2fr]">
          <div className="space-y-6">
            <div>
              <h2 className="text-3xl font-bold lg:text-4xl">{copy.liveTitle}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{copy.liveSubtitle}</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              {pulseStats.map((stat) => (
                <Card
                  key={stat.label}
                  className="relative overflow-hidden border-primary/30 bg-gradient-to-br from-primary/10 via-background to-background"
                >
                  <div className="pointer-events-none absolute inset-px rounded-2xl bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.08),_transparent_65%)]" />
                  <div className="relative flex flex-col gap-2 p-5">
                    <span className="text-xs font-semibold uppercase tracking-wide text-primary">
                      {stat.label}
                    </span>
                    <span className="text-2xl font-semibold text-foreground">{stat.value}</span>
                  </div>
                </Card>
              ))}
            </div>
            <Card className="relative overflow-hidden border-primary/20 bg-background/80">
              <div className="pointer-events-none absolute -right-24 top-1/2 h-56 w-56 -translate-y-1/2 bg-[radial-gradient(rgba(59,130,246,0.25),transparent_70%)] blur-3xl" />
              <div className="relative flex items-start gap-3 p-6">
                <BarChart3 className="h-6 w-6 text-primary" />
                <div>
                  <div className="text-sm font-semibold text-foreground">{copy.brand}</div>
                  <p className="mt-1 text-sm text-muted-foreground">{copy.liveAssist}</p>
                </div>
              </div>
            </Card>
          </div>
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Compass className="h-5 w-5 text-primary" />
              <h3 className="text-lg font-semibold text-foreground">
                {copy.liveTitle}
              </h3>
            </div>
            <div className="rounded-3xl border border-muted bg-background/80 shadow-sm backdrop-blur">
              <div className="overflow-hidden rounded-3xl">
                <div className="grid grid-cols-[minmax(0,2fr)_auto_auto_auto] bg-muted/40 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  <span>{copy.liveTable.token}</span>
                  <span className="text-right">{copy.liveTable.score}</span>
                  <span className="text-right">{copy.liveTable.pools}</span>
                  <span className="text-right">{copy.liveTable.liquidity}</span>
                </div>
                {topTokens.length > 0 ? (
                  topTokens.slice(0, 10).map((token) => (
                    <div
                      key={`pulse-${token.mint_address}`}
                      className="grid grid-cols-[minmax(0,2fr)_auto_auto_auto] items-center px-4 py-3 text-sm transition hover:bg-muted/25"
                    >
                      <div>
                        <div className="font-semibold">
                          {token.symbol || token.name || token.mint_address.slice(0, 6)}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {token.mint_address.slice(0, 4)}…{token.mint_address.slice(-4)}
                        </div>
                      </div>
                      <div className="text-right font-semibold text-primary">
                        {token.score?.toFixed(3)}
                      </div>
                      <div className="text-right text-sm text-muted-foreground">
                        {token.pools?.length ?? 0}
                      </div>
                      <div className="text-right text-sm font-semibold text-foreground">
                        {formatCurrency(token.liquidity_usd)}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="px-4 py-6 text-sm text-muted-foreground">{copy.liveTable.empty}</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-muted/40 py-16">
        <div className="mx-auto max-w-5xl px-4 lg:px-8">
          <h2 className="mb-10 text-center text-3xl font-bold lg:text-4xl">
            {copy.advantagesTitle}
          </h2>
          <div className="grid gap-6 md:grid-cols-3">
            {copy.advantages.map(
              (item: { title: string; description: string }, index: number) => {
                const Icon = [Target, ShieldCheck, Sparkles][index] ?? Target
                return (
                  <div
                    key={item.title}
                    className="rounded-xl border border-muted bg-background p-6 shadow-sm"
                  >
                    <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="text-lg font-semibold">{item.title}</h3>
                    <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
                  </div>
                )
              }
            )}
          </div>
        </div>
      </section>

      <section className="relative mx-auto max-w-5xl px-4 py-16 lg:px-8">
        <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(60%_60%_at_30%_20%,rgba(139,92,246,0.12),transparent)]" />
        <h2 className="mb-10 text-center text-3xl font-bold lg:text-4xl">
          {copy.integrationsTitle}
        </h2>
        <div className="grid gap-6 md:grid-cols-3">
          {copy.integrations.map(
            (card: { title: string; description: string }, index: number) => {
              const Icon = [Plug, Bot, Sparkles][index] ?? Plug
              const cardContent = (
                <div className="flex h-full flex-col rounded-xl border border-muted bg-card/70 p-6 shadow-sm transition hover:border-primary">
                  <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-lg font-semibold">{card.title}</h3>
                  <p className="mt-2 flex-1 text-sm text-muted-foreground">{card.description}</p>
                  <div className="mt-4 text-xs uppercase tracking-wide text-muted-foreground">
                    beta
                  </div>
                </div>
              )
              return <div key={card.title}>{cardContent}</div>
            }
          )}
        </div>
      </section>

      <section className="bg-muted/40 py-16">
        <div className="relative mx-auto max-w-4xl px-4 lg:px-8">
          <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(60%_60%_at_70%_40%,rgba(250,204,21,0.15),transparent)]" />
          <h2 className="mb-10 text-center text-3xl font-bold lg:text-4xl">{copy.howToTitle}</h2>
          <div className="grid gap-8 md:grid-cols-3">
            {copy.steps.map(
              (step: { title: string; description: string }, index: number) => (
                <div key={step.title} className="rounded-xl border border-muted bg-background p-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground shadow">
                    {index + 1}
                  </div>
                  <h3 className="mt-4 text-lg font-semibold">{step.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{step.description}</p>
                </div>
              )
            )}
          </div>
          <div className="mt-12 rounded-2xl border border-primary/20 bg-background/70 p-6 shadow-sm backdrop-blur">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <h3 className="text-xl font-semibold">{copy.subscribe.title}</h3>
                <p className="text-sm text-muted-foreground">{copy.subscribe.description}</p>
              </div>
              <Button size="lg" variant="secondary" asChild>
                <a href="/app/">
                  <Send className="mr-2 h-4 w-4" />
                  {copy.subscribe.button}
                </a>
              </Button>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-4xl px-4 py-16 lg:px-8">
        <h2 className="mb-6 text-center text-3xl font-bold lg:text-4xl">{copy.communityTitle}</h2>
        <div className="mx-auto max-w-xl">
          <div className="space-y-6 border-l border-muted pl-6">
            {copy.timeline.map(
              (item: { period: string; label: string }, index: number) => (
                <div key={item.period} className="relative">
                  <div className="absolute -left-[33px] flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground shadow">
                    {index + 1}
                  </div>
                  <div className="text-sm font-semibold">{item.period}</div>
                  <div className="text-sm text-muted-foreground">{item.label}</div>
                </div>
              )
            )}
          </div>
        </div>
      </section>

      <footer className="border-t border-muted bg-muted/30">
        <div className="mx-auto flex max-w-5xl flex-col gap-6 px-4 py-12 text-center lg:px-8">
          <p className="text-sm text-muted-foreground">{copy.footer.beta}</p>
          <div className="flex flex-wrap justify-center gap-3">
            <Button asChild>
              <a href="/app/">{copy.footer.login}</a>
            </Button>
            <Button variant="outline" asChild>
              <a href="/app/">{copy.footer.register}</a>
            </Button>
          </div>
        </div>
      </footer>
    </div>
  )
}
