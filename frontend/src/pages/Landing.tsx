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
import { useLanguage } from '@/hooks/useLanguage'
import { useTokenStats } from '@/hooks/useTokenStats'
import { useTokens } from '@/hooks/useTokens'
import { formatCurrency } from '@/lib/utils'

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
    stats: {
      fresh: 'Fresh tokens (24h)',
      avgLiquidity: 'Average liquidity',
      totalTokens: 'Tokens in system',
      newPools: 'New pools (24h)',
      newCoins: 'New coins (24h)',
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
        action: 'API Docs',
        href: '/api-docs',
      },
      {
        title: 'NotArb & SolanaMevBot ready',
        description: 'Download fresh markets.json configs with pool bundles in one click.',
        action: 'Download',
        href: '/notarb/markets',
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
      title: 'Stay in the loop',
      description: 'Join our Telegram channel for instant updates, alpha and release notes.',
      button: 'Open Telegram',
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
    stats: {
      fresh: 'Свежие токены (24ч)',
      avgLiquidity: 'Средняя ликвидность',
      totalTokens: 'Токенов в системе',
      newPools: 'Новые пулы (24ч)',
      newCoins: 'Новые монеты (24ч)',
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
        action: 'Открыть документацию',
        href: '/api-docs',
      },
      {
        title: 'Готово для NotArb и SolanaMevBot',
        description: 'Скачай актуальный markets.json с готовыми пулами.',
        action: 'Скачать',
        href: '/notarb/markets',
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
      title: 'Будь в курсе',
      description: 'Подпишись на Telegram-канал с обновлениями, альфой и анонсами релизов.',
      button: 'Открыть Telegram',
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

export default function Landing() {
  const { language } = useLanguage()
  const lang: Lang = language === 'ru' ? 'ru' : 'en'
  const copy = TEXT[lang]

  const { data: stats } = useTokenStats()
  const { data: activeTokens } = useTokens(ACTIVE_FILTER)
  const { data: monitoringTokens } = useTokens(MONITORING_FILTER)

  const {
    freshCount,
    avgLiquidity,
    newPoolsCount,
    topTokens,
  } = useMemo(() => {
    const now = Date.now()
    const active = activeTokens?.items ?? []
    const monitoring = monitoringTokens?.items ?? []
    const combined = [...active, ...monitoring]

    const fresh = combined.filter((token) => {
      if (!token.created_at) return false
      const created = Date.parse(token.created_at)
      if (Number.isNaN(created)) return false
      return now - created <= ONE_DAY
    })

    const pools24h = fresh.filter((token) => (token.pools ?? []).length > 0)

    const liquidityValues = active
      .map((token) => Number(token.liquidity_usd))
      .filter((value) => Number.isFinite(value) && value > 0)

    const avgLiq =
      liquidityValues.length > 0
        ? liquidityValues.reduce((sum, value) => sum + value, 0) / liquidityValues.length
        : undefined

    return {
      freshCount: fresh.length,
      avgLiquidity: avgLiq,
      newPoolsCount: pools24h.length,
      topTokens: active.slice(0, 5),
    }
  }, [activeTokens, monitoringTokens])

  const heroStats = [
    {
      label: copy.stats.fresh,
      value: formatInteger(freshCount),
    },
    {
      label: copy.stats.avgLiquidity,
      value: avgLiquidity !== undefined ? formatCurrency(avgLiquidity) : '—',
    },
    {
      label: copy.stats.totalTokens,
      value: formatInteger(stats?.total),
    },
  ]

  const barMax = Math.max(freshCount || 0, newPoolsCount || 0, 1)

  return (
    <div className="min-h-screen bg-background text-foreground">
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-background to-background" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(123,97,255,0.25),_transparent_60%)]" />
        <div className="relative mx-auto flex max-w-6xl flex-col gap-12 px-4 pb-20 pt-24 lg:px-8 lg:pt-28">
          <div className="flex flex-col gap-8 lg:flex-row lg:items-center">
            <div className="flex-1 space-y-6">
              <span className="inline-flex items-center rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-primary">
                Beta access
              </span>
              <h1 className="text-4xl font-bold leading-tight tracking-tight md:text-5xl lg:text-6xl">
                {copy.heroTitle}
              </h1>
              <p className="max-w-2xl text-lg text-muted-foreground md:text-xl">
                {copy.heroSubtitle}
              </p>
              <div className="flex flex-wrap gap-3">
                <Button size="lg" asChild>
                  <a href="/login">
                    {copy.ctaLogin}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </a>
                </Button>
                <Button size="lg" variant="outline" asChild>
                  <a href="/register">{copy.ctaRegister}</a>
                </Button>
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                {heroStats.map((stat) => (
                  <div
                    key={stat.label}
                    className="rounded-xl border border-primary/20 bg-background/60 p-4 backdrop-blur"
                  >
                    <div className="text-2xl font-semibold text-foreground">{stat.value}</div>
                    <div className="text-sm text-muted-foreground">{stat.label}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex-1">
              <div className="rounded-2xl border border-primary/20 bg-background/80 p-6 shadow-xl backdrop-blur">
                <div className="mb-4 flex items-center justify-between">
                  <div className="font-semibold text-muted-foreground">{copy.liveTitle}</div>
                  <Sparkles className="h-5 w-5 text-primary" />
                </div>
                <div className="flex flex-col gap-3">
                  {topTokens.map((token) => (
                    <div
                      key={token.mint_address}
                      className="flex items-center justify-between rounded-lg border border-muted px-3 py-2"
                    >
                      <div>
                        <div className="text-sm font-medium">
                          {token.symbol || token.name || token.mint_address.slice(0, 6)}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {token.mint_address.slice(0, 4)}…{token.mint_address.slice(-4)}
                        </div>
                      </div>
                      <div className="text-right text-sm font-semibold text-primary">
                        {token.score?.toFixed(3)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-16 lg:px-8">
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

      <section className="mx-auto max-w-6xl px-4 py-16 lg:px-8">
        <div className="grid gap-12 lg:grid-cols-[3fr_2fr]">
          <div>
            <h2 className="mb-6 text-3xl font-bold lg:text-4xl">{copy.liveTitle}</h2>
            <div className="flex gap-4 overflow-x-auto pb-4">
              {topTokens.map((token) => (
                <div
                  key={`card-${token.mint_address}`}
                  className="min-w-[220px] rounded-xl border border-muted bg-card/80 p-4 shadow-sm"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold">
                      {token.symbol || token.name || token.mint_address.slice(0, 6)}
                    </span>
                    <span className="text-xs text-muted-foreground">score</span>
                  </div>
                  <div className="mt-2 text-2xl font-bold text-primary">
                    {token.score?.toFixed(3)}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {formatCurrency(token.liquidity_usd)}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="space-y-6">
            <div className="rounded-xl border border-muted bg-card/80 p-6 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <span className="text-sm font-semibold">{copy.stats.newCoins}</span>
                <BarChart3 className="h-5 w-5 text-primary" />
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div
                  className="h-2 rounded-full bg-primary"
                  style={{ width: `${Math.min(100, (freshCount / barMax) * 100)}%` }}
                />
              </div>
              <div className="mt-2 text-2xl font-semibold">{formatInteger(freshCount)}</div>
            </div>
            <div className="rounded-xl border border-muted bg-card/80 p-6 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <span className="text-sm font-semibold">{copy.stats.newPools}</span>
                <Compass className="h-5 w-5 text-primary" />
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div
                  className="h-2 rounded-full bg-primary/70"
                  style={{ width: `${Math.min(100, (newPoolsCount / barMax) * 100)}%` }}
                />
              </div>
              <div className="mt-2 text-2xl font-semibold">{formatInteger(newPoolsCount)}</div>
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

      <section className="mx-auto max-w-5xl px-4 py-16 lg:px-8">
        <h2 className="mb-10 text-center text-3xl font-bold lg:text-4xl">
          {copy.integrationsTitle}
        </h2>
        <div className="grid gap-6 md:grid-cols-3">
          {copy.integrations.map(
            (
              card: { title: string; description: string; action?: string; href?: string },
              index: number
            ) => {
              const Icon = [Plug, Bot, Sparkles][index] ?? Plug
              const cardContent = (
                <div className="flex h-full flex-col rounded-xl border border-muted bg-card/70 p-6 shadow-sm transition hover:border-primary">
                  <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-lg font-semibold">{card.title}</h3>
                  <p className="mt-2 flex-1 text-sm text-muted-foreground">{card.description}</p>
                  {card.action && card.href && (
                    <Button variant="link" className="justify-start px-0" asChild>
                      <a href={card.href} className="text-primary">
                        {card.action}
                        <ArrowRight className="ml-1 h-4 w-4" />
                      </a>
                    </Button>
                  )}
                </div>
              )
              return <div key={card.title}>{cardContent}</div>
            }
          )}
        </div>
      </section>

      <section className="bg-muted/40 py-16">
        <div className="mx-auto max-w-4xl px-4 lg:px-8">
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
                <a href="https://t.me/tothemoon_arbitrage" target="_blank" rel="noreferrer">
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
              <a href="/login">{copy.footer.login}</a>
            </Button>
            <Button variant="outline" asChild>
              <a href="/register">{copy.footer.register}</a>
            </Button>
          </div>
        </div>
      </footer>
    </div>
  )
}
