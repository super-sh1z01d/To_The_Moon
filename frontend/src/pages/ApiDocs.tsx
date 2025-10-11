import { useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useLanguage } from '@/hooks/useLanguage'
import { usePageMetadata } from '@/hooks/usePageMetadata'

type Language = 'en' | 'ru'

type Parameter = {
  name: string
  optional?: boolean
  description: Record<Language, string>
  type: 'query' | 'path'
}

type Endpoint = {
  method: 'GET'
  path: string
  title: Record<Language, string>
  description: Record<Language, string>
  parameters?: Parameter[]
  exampleRequest: Record<Language, string>
  exampleResponse: Record<Language, string>
  notes?: Record<Language, string>[]
}

type DocsByLanguage = Record<Language, Endpoint[]>

const API_ENDPOINTS: DocsByLanguage = {
  en: [
    {
      method: 'GET',
      path: '/tokens',
      title: {
        en: 'List tokens',
        ru: 'Получение списка токенов',
      },
      description: {
        en: 'Returns a paginated list of tokens with the latest score snapshot, liquidity and activity metrics. Useful for leaderboards, bots and dashboards.',
        ru: 'Возвращает постраничный список токенов с последним снапшотом скоринга, ликвидностью и активностью. Подходит для витрин, ботов и аналитики.',
      },
      parameters: [
        {
          name: 'status',
          optional: true,
          type: 'query',
          description: {
            en: 'Filter by status (active, monitoring, archived). You can pass a single value with `status=` or several via `statuses=active,monitoring`.',
            ru: 'Фильтр по статусу (active, monitoring, archived). Можно передавать одиночное значение через `status=` или несколько через `statuses=active,monitoring`.',
          },
        },
        {
          name: 'limit',
          optional: true,
          type: 'query',
          description: {
            en: 'Maximum number of tokens per page (1–100). Default: 50.',
            ru: 'Максимальное количество токенов на странице (1–100). По умолчанию 50.',
          },
        },
        {
          name: 'offset',
          optional: true,
          type: 'query',
          description: {
            en: 'Offset for pagination. Combine with limit to walk through the list.',
            ru: 'Смещение для постраничной навигации. Используйте вместе с limit.',
          },
        },
        {
          name: 'min_score',
          optional: true,
          type: 'query',
          description: {
            en: 'Return only tokens with score not lower than the provided value.',
            ru: 'Возвращает только токены со скором не ниже указанного значения.',
          },
        },
      ],
      exampleRequest: {
        en: "curl -s 'https://tothemoon.sh1z01d.ru/tokens?status=active&limit=5'",
        ru: "curl -s 'https://tothemoon.sh1z01d.ru/tokens?status=active&limit=5'",
      },
      exampleResponse: {
        en: `{
  "total": 52,
  "items": [
    {
      "mint_address": "Drp4cgSrhQERpDyjZCujGJRSp2m8dbD7B8i7bqkqpump",
      "symbol": "BOOST",
      "status": "active",
      "score": 1.6459,
      "liquidity_usd": 59291.0,
      "delta_p_5m": 0.0242,
      "n_5m": 666,
      "primary_dex": "pumpswap",
      "fetched_at": "2025-10-10T19:23:34.100492+00:00",
      "scored_at": "2025-10-10T19:23:34.102129+00:00"
    }
  ],
  "meta": {
    "limit": 5,
    "offset": 0,
    "sort": "score_desc",
    "page": 1,
    "has_next": true
  }
}`,
        ru: `{
  "total": 52,
  "items": [
    {
      "mint_address": "Drp4cgSrhQERpDyjZCujGJRSp2m8dbD7B8i7bqkqpump",
      "symbol": "BOOST",
      "status": "active",
      "score": 1.6459,
      "liquidity_usd": 59291.0,
      "delta_p_5m": 0.0242,
      "n_5m": 666,
      "primary_dex": "pumpswap",
      "fetched_at": "2025-10-10T19:23:34.100492+00:00",
      "scored_at": "2025-10-10T19:23:34.102129+00:00"
    }
  ],
  "meta": {
    "limit": 5,
    "offset": 0,
    "sort": "score_desc",
    "page": 1,
    "has_next": true
  }
}`,
      },
    },
    {
      method: 'GET',
      path: '/tokens/{mint}',
      title: {
        en: 'Token detail',
        ru: 'Детали конкретного токена',
      },
      description: {
        en: 'Fetches the latest metrics and score history for a specific token.',
        ru: 'Возвращает актуальные метрики и историю скоринга для выбранного токена.',
      },
      parameters: [
        {
          name: 'mint',
          type: 'path',
          description: {
            en: 'Mint address of the token (Base58).',
            ru: 'Mint-адрес токена (Base58).',
          },
        },
        {
          name: 'history_limit',
          optional: true,
          type: 'query',
          description: {
            en: 'How many score snapshots to return (default 20, max 200).',
            ru: 'Сколько снапшотов истории вернуть (по умолчанию 20, максимум 200).',
          },
        },
      ],
      exampleRequest: {
        en: "curl -s 'https://tothemoon.sh1z01d.ru/tokens/Drp4cgSrhQERpDyjZCujGJRSp2m8dbD7B8i7bqkqpump'",
        ru: "curl -s 'https://tothemoon.sh1z01d.ru/tokens/Drp4cgSrhQERpDyjZCujGJRSp2m8dbD7B8i7bqkqpump'",
      },
      exampleResponse: {
        en: `{
  "mint_address": "Drp4cgSrhQERpDyjZCujGJRSp2m8dbD7B8i7bqkqpump",
  "symbol": "BOOST",
  "status": "active",
  "score": 1.6459,
  "liquidity_usd": 59291.0,
  "metrics": {
    "L_tot": 59291.0,
    "delta_p_5m": 0.0242,
    "delta_p_15m": 0.4025,
    "n_5m": 666
  },
  "score_history": [
    {
      "created_at": "2025-10-10T19:23:34.102129+00:00",
      "score": 1.6459
    }
  ],
  "pools": [
    {
      "dex": "pumpswap",
      "quote": "SOL"
    }
  ]
}`,
        ru: `{
  "mint_address": "Drp4cgSrhQERpDyjZCujGJRSp2m8dbD7B8i7bqkqpump",
  "symbol": "BOOST",
  "status": "active",
  "score": 1.6459,
  "liquidity_usd": 59291.0,
  "metrics": {
    "L_tot": 59291.0,
    "delta_p_5m": 0.0242,
    "delta_p_15m": 0.4025,
    "n_5m": 666
  },
  "score_history": [
    {
      "created_at": "2025-10-10T19:23:34.102129+00:00",
      "score": 1.6459
    }
  ],
  "pools": [
    {
      "dex": "pumpswap",
      "quote": "SOL"
    }
  ]
}`,
      },
    },
    {
      method: 'GET',
      path: '/tokens/stats',
      title: {
        en: 'Token counters by status',
        ru: 'Статистика по статусам',
      },
      description: {
        en: 'Lightweight helper endpoint that returns how many tokens are active, in monitoring, or archived.',
        ru: 'Лёгкий вспомогательный эндпоинт: показывает, сколько токенов активно, в мониторинге и в архиве.',
      },
      exampleRequest: {
        en: "curl -s 'https://tothemoon.sh1z01d.ru/tokens/stats'",
        ru: "curl -s 'https://tothemoon.sh1z01d.ru/tokens/stats'",
      },
      exampleResponse: {
        en: `{
  "total": 2450,
  "active": 15,
  "monitoring": 39,
  "archived": 2396
}`,
        ru: `{
  "total": 2450,
  "active": 15,
  "monitoring": 39,
  "archived": 2396
}`,
      },
    },
    {
      method: 'GET',
      path: '/tokens/{mint}/pools',
      title: {
        en: 'Token pools',
        ru: 'Пулы токена',
      },
      description: {
        en: 'Returns WSOL/USDC pools that passed internal filters. Useful for routing liquidity or building DEX widgets.',
        ru: 'Возвращает пулы WSOL/USDC, прошедшие фильтрацию. Подходит для построения маршрутизации ликвидности и виджетов DEX.',
      },
      parameters: [
        {
          name: 'mint',
          type: 'path',
          description: {
            en: 'Mint address of the token.',
            ru: 'Mint-адрес токена.',
          },
        },
      ],
      exampleRequest: {
        en: "curl -s 'https://tothemoon.sh1z01d.ru/tokens/Drp4cgSrhQERpDyjZCujGJRSp2m8dbD7B8i7bqkqpump/pools'",
        ru: "curl -s 'https://tothemoon.sh1z01d.ru/tokens/Drp4cgSrhQERpDyjZCujGJRSp2m8dbD7B8i7bqkqpump/pools'",
      },
      exampleResponse: {
        en: `[
  {
    "address": "6qzditW8XWhjfVRbkHjZ7HDJnHrJhJJNGAnsjV4bWQZP",
    "dex": "pumpswap",
    "quote": "SOL"
  },
  {
    "address": "4H8Dmw1feFf1uZSVbjzjgQsvHw8QPcSkXsErC7qhCLCX",
    "dex": "meteora",
    "quote": "SOL"
  }
]`,
        ru: `[
  {
    "address": "6qzditW8XWhjfVRbkHjZ7HDJnHrJhJJNGAnsjV4bWQZP",
    "dex": "pumpswap",
    "quote": "SOL"
  },
  {
    "address": "4H8Dmw1feFf1uZSVbjzjgQsvHw8QPcSkXsErC7qhCLCX",
    "dex": "meteora",
    "quote": "SOL"
  }
]`,
      },
      notes: [
        {
          en: 'If latest snapshot is missing pool data, the service will fetch pairs on the fly via DexScreener.',
          ru: 'Если в последнем снапшоте нет пулов, сервис подгрузит пары на лету через DexScreener.',
        },
      ],
    },
    {
      method: 'GET',
      path: '/notarb/markets',
      title: {
        en: 'NotArb markets feed',
        ru: 'Поток рынков для NotArb',
      },
      description: {
        en: 'Returns the curated `markets.json` file used by the NotArb bot (token metadata plus pool lists). Alias `/notarb/markets.json` serves the same payload.',
        ru: 'Возвращает подготовленный файл `markets.json`, который использует бот NotArb (метаданные токена и список пулов). Алиас `/notarb/markets.json` отдаёт тот же JSON.',
      },
      exampleRequest: {
        en: "curl -s 'https://tothemoon.sh1z01d.ru/notarb/markets?limit=5' | jq '.tokens[0]'",
        ru: "curl -s 'https://tothemoon.sh1z01d.ru/notarb/markets?limit=5' | jq '.tokens[0]'",
      },
      exampleResponse: {
        en: `{
  "tokens": [
    {
      "mint": "Drp4cgSrhQERpDyjZCujGJRSp2m8dbD7B8i7bqkqpump",
      "symbol": "BOOST",
      "score": 1.6459,
      "pools": [
        "6qzditW8XWhjfVRbkHjZ7HDJnHrJhJJNGAnsjV4bWQZP",
        "4H8Dmw1feFf1uZSVbjzjgQsvHw8QPcSkXsErC7qhCLCX"
      ]
    }
  ],
  "metadata": {
    "min_score_threshold": 0.5,
    "generated_at": "2025-10-10T19:23:34.000000+00:00"
  }
}`,
        ru: `{
  "tokens": [
    {
      "mint": "Drp4cgSrhQERpDyjZCujGJRSp2m8dbD7B8i7bqkqpump",
      "symbol": "BOOST",
      "score": 1.6459,
      "pools": [
        "6qzditW8XWhjfVRbkHjZ7HDJnHrJhJJNGAnsjV4bWQZP",
        "4H8Dmw1feFf1uZSVbjzjgQsvHw8QPcSkXsErC7qhCLCX"
      ]
    }
  ],
  "metadata": {
    "min_score_threshold": 0.5,
    "generated_at": "2025-10-10T19:23:34.000000+00:00"
  }
}`,
      },
      notes: [
        {
          en: 'The file is refreshed by the scheduler; for manual export use the private `/notarb/export` endpoint.',
          ru: 'Файл обновляется шедулером; для принудительной выгрузки есть внутренний эндпоинт `/notarb/export`.',
        },
      ],
    },
  ],
  ru: []
}

// Populate Russian list by reusing English structure for convenience
type MutableDocs = DocsByLanguage & { ru: Endpoint[] }
;(API_ENDPOINTS as MutableDocs).ru = API_ENDPOINTS.en.map((endpoint) => ({
  ...endpoint,
}))

const INTRO_TEXT: Record<Language, string> = {
  en: 'These endpoints are safe to expose publicly. Each response is cached-friendly and does not mutate state.',
  ru: 'Эти эндпоинты безопасно открывать наружу. Они кэшируются и не изменяют состояние сервиса.',
}

const LABELS = {
  parameters: {
    en: 'Parameters',
    ru: 'Параметры',
  },
  query: {
    en: 'Query parameters',
    ru: 'Параметры запроса',
  },
  path: {
    en: 'Path parameters',
    ru: 'Параметры пути',
  },
  optional: {
    en: 'optional',
    ru: 'необязательный',
  },
  exampleRequest: {
    en: 'Example request',
    ru: 'Пример запроса',
  },
  exampleResponse: {
    en: 'Example response',
    ru: 'Пример ответа',
  },
  notes: {
    en: 'Notes',
    ru: 'Примечания',
  },
  heading: {
    en: 'Public API Overview',
    ru: 'Документация публичного API',
  },
}

function CodeBlock({ children }: { children: string }) {
  return (
    <pre className="mt-3 overflow-x-auto rounded-md bg-muted p-4 text-xs leading-relaxed">
      <code>{children}</code>
    </pre>
  )
}

export default function ApiDocs() {
  const { language } = useLanguage()
  const lang = (language as Language) || 'en'
  const endpoints = API_ENDPOINTS[lang]
  const docsMetadata = useMemo(() => {
    const origin = typeof window !== 'undefined' ? window.location.origin : 'https://tothemoon.sh1z01d.ru'
    return {
      en: {
        title: 'API Documentation | To The Moon',
        description: 'Integrate To The Moon intelligence via REST endpoints, markets.json exports and WebSocket streams for Solana arbitrage bots.',
        keywords: ['solana api', 'arbitrage data', 'markets json', 'websocket streams'],
      },
      ru: {
        title: 'API документация | To The Moon',
        description: 'Интегрируйте данные To The Moon через REST API, экспорт markets.json и WebSocket-потоки для арбитражных ботов.',
        keywords: ['solana api', 'данные арбитража', 'markets json', 'websocket'],
      },
      canonical: `${origin}/app/api-docs`,
      siteName: 'To The Moon',
      ogType: 'article',
    }
  }, [])

  usePageMetadata(docsMetadata)

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-3xl">{LABELS.heading[lang]}</CardTitle>
          <CardDescription>{INTRO_TEXT[lang]}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {endpoints.map((endpoint) => (
              <Card key={`${lang}-${endpoint.path}`}>
                <CardHeader className="space-y-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge variant="secondary" className="uppercase tracking-wide">
                      {endpoint.method}
                    </Badge>
                    <code className="text-sm font-mono text-muted-foreground">
                      {endpoint.path}
                    </code>
                  </div>
                  <CardTitle className="text-xl">
                    {endpoint.title[lang]}
                  </CardTitle>
                  <CardDescription>
                    {endpoint.description[lang]}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {endpoint.parameters && endpoint.parameters.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold">
                        {LABELS.parameters[lang]}
                      </h4>
                      <div className="mt-2 space-y-3">
                        {endpoint.parameters.map((param) => (
                          <div key={`${endpoint.path}-${param.type}-${param.name}`} className="rounded-md border p-3 text-sm">
                            <div className="flex flex-wrap items-center gap-2 text-foreground">
                              <span className="font-mono">{param.name}</span>
                              <Badge variant="outline" className="uppercase">
                                {LABELS[param.type][lang]}
                              </Badge>
                              {param.optional && (
                                <Badge variant="outline" className="uppercase">
                                  {LABELS.optional[lang]}
                                </Badge>
                              )}
                            </div>
                            <p className="mt-2 text-muted-foreground">
                              {param.description[lang]}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div>
                    <h4 className="text-sm font-semibold">
                      {LABELS.exampleRequest[lang]}
                    </h4>
                    <CodeBlock>{endpoint.exampleRequest[lang]}</CodeBlock>
                  </div>

                  <div>
                    <h4 className="text-sm font-semibold">
                      {LABELS.exampleResponse[lang]}
                    </h4>
                    <CodeBlock>{endpoint.exampleResponse[lang]}</CodeBlock>
                  </div>

                  {endpoint.notes && endpoint.notes.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold">{LABELS.notes[lang]}</h4>
                      <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                        {endpoint.notes.map((note, index) => (
                          <li key={`${endpoint.path}-note-${index}`}>• {note[lang]}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
