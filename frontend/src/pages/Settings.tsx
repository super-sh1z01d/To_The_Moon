import { useEffect, useState } from 'react'
import { getSettingsIndividually, putSetting, recalc, SettingsMap, getActiveModel } from '../lib/api'

const arbitrageKeys = [
  'w_tx', 'w_fresh', 'ewma_alpha', 'freshness_threshold_hours',
  'arbitrage_min_tx_5m', 'arbitrage_optimal_tx_5m', 'arbitrage_acceleration_weight',
  'min_score', 'activation_min_liquidity_usd', 'min_pool_liquidity_usd', 
  'hot_interval_sec', 'cold_interval_sec', 'archive_below_hours', 'monitoring_timeout_hours',
  'notarb_min_score', 'notarb_max_spam_percentage',
  'backlog_warning_threshold', 'backlog_error_threshold', 'backlog_critical_threshold',
  'spam_whitelist_wallets'
]

export default function Settings() {
  const [vals, setVals] = useState<SettingsMap>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string>('')

  useEffect(() => {
    (async () => {
      setLoading(true)
      try {
        const settings = await getSettingsIndividually(arbitrageKeys)
        setVals(settings)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const update = (k: string, v: string) => setVals(prev => ({ ...prev, [k]: v }))

  async function save(recalculate: boolean) {
    setSaving(true)
    setMessage('')
    try {
      const settingsToUpdate = arbitrageKeys.filter(k => vals[k] != null)
      await Promise.all(settingsToUpdate.map(k => putSetting(k, String(vals[k]))))
      if (recalculate) {
        await recalc()
      }
      setMessage(recalculate ? 'Сохранено. Пересчёт запущен.' : 'Сохранено.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div>Загрузка...</div>

  const wTx = parseFloat(vals['w_tx'] || '0.6')
  const wFresh = parseFloat(vals['w_fresh'] || '0.4')

  return (
    <div>
      <h2>🎯 Настройки арбитражной системы</h2>
      
      {message && (
        <div style={{ 
          background: '#d4edda', 
          padding: 12, 
          borderRadius: 4, 
          marginBottom: 16,
          border: '1px solid #c3e6cb'
        }}>
          {message}
        </div>
      )}

      <section style={{ marginBottom: 24 }}>
        <h3>⚖️ Веса компонентов</h3>
        <div style={{ background: 'white', padding: 16, borderRadius: 8, border: '1px solid #dee2e6' }}>
          
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
              🔥 TX Acceleration ({(wTx * 100).toFixed(0)}%)
            </label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="1"
              value={vals['w_tx'] || '0.6'}
              onChange={(e) => update('w_tx', e.target.value)}
              style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
              🆕 Token Freshness ({(wFresh * 100).toFixed(0)}%)
            </label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="1"
              value={vals['w_fresh'] || '0.4'}
              onChange={(e) => update('w_fresh', e.target.value)}
              style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
            />
          </div>

          <div style={{ fontFamily: 'monospace', background: '#f8f9fa', padding: 8, borderRadius: 4 }}>
            <strong>Формула:</strong> Score = {wTx.toFixed(1)}×TX + {wFresh.toFixed(1)}×Fresh
          </div>
        </div>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h3>🔥 Арбитражные пороги TX</h3>
        <div style={{ background: 'white', padding: 16, borderRadius: 8, border: '1px solid #dee2e6' }}>
          
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
              Минимальный порог (TX/5мин)
            </label>
            <input
              type="number"
              step="10"
              min="1"
              max="200"
              value={vals['arbitrage_min_tx_5m'] || '50'}
              onChange={(e) => update('arbitrage_min_tx_5m', e.target.value)}
              style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
            />
            <small style={{ color: '#666' }}>
              Минимальная активность для начала расчета TX компонента.
            </small>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
              Оптимальный порог (TX/5мин)
            </label>
            <input
              type="number"
              step="10"
              min="50"
              max="500"
              value={vals['arbitrage_optimal_tx_5m'] || '200'}
              onChange={(e) => update('arbitrage_optimal_tx_5m', e.target.value)}
              style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
            />
            <small style={{ color: '#666' }}>
              Активность для максимального TX скора. Оптимально для арбитражных ботов.
            </small>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
              Вес ускорения
            </label>
            <input
              type="number"
              step="0.1"
              min="0.1"
              max="0.9"
              value={vals['arbitrage_acceleration_weight'] || '0.3'}
              onChange={(e) => update('arbitrage_acceleration_weight', e.target.value)}
              style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
            />
            <small style={{ color: '#666' }}>
              Доля ускорения в TX компоненте. Остальное - абсолютная активность.
            </small>
          </div>
        </div>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h3>📊 Параметры сглаживания</h3>
        <div style={{ background: 'white', padding: 16, borderRadius: 8, border: '1px solid #dee2e6' }}>
          
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
              EWMA Alpha
            </label>
            <input
              type="number"
              step="0.1"
              min="0.1"
              max="1.0"
              value={vals['ewma_alpha'] || '0.8'}
              onChange={(e) => update('ewma_alpha', e.target.value)}
              style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
            />
            <small style={{ color: '#666' }}>
              Скорость адаптации к изменениям. 0.1 = стабильно, 1.0 = быстро реагирует.
            </small>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
              Порог свежести (часы)
            </label>
            <input
              type="number"
              step="1"
              min="1"
              max="24"
              value={vals['freshness_threshold_hours'] || '6'}
              onChange={(e) => update('freshness_threshold_hours', e.target.value)}
              style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
            />
            <small style={{ color: '#666' }}>
              Сколько часов токен получает бонус за свежесть после миграции.
            </small>
          </div>
        </div>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h3>⚙️ Системные параметры</h3>
        <div style={{ background: 'white', padding: 16, borderRadius: 8, border: '1px solid #dee2e6' }}>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
                Мин. скор
              </label>
              <input
                type="number"
                step="0.05"
                min="0"
                max="1"
                value={vals['min_score'] || '0.15'}
                onChange={(e) => update('min_score', e.target.value)}
                style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
                🚀 Активация ($)
              </label>
              <input
                type="number"
                step="50"
                min="50"
                max="1000"
                value={vals['activation_min_liquidity_usd'] || '200'}
                onChange={(e) => update('activation_min_liquidity_usd', e.target.value)}
                style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
                💧 Мин. ликвидность ($)
              </label>
              <input
                type="number"
                step="100"
                min="100"
                max="2000"
                value={vals['min_pool_liquidity_usd'] || '500'}
                onChange={(e) => update('min_pool_liquidity_usd', e.target.value)}
                style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
                Hot интервал (сек)
              </label>
              <input
                type="number"
                step="5"
                min="5"
                max="60"
                value={vals['hot_interval_sec'] || '10'}
                onChange={(e) => update('hot_interval_sec', e.target.value)}
                style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
                Cold интервал (сек)
              </label>
              <input
                type="number"
                step="5"
                min="30"
                max="300"
                value={vals['cold_interval_sec'] || '45'}
                onChange={(e) => update('cold_interval_sec', e.target.value)}
                style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
                NotArb скор
              </label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                max="1"
                value={vals['notarb_min_score'] || '0.5'}
                onChange={(e) => update('notarb_min_score', e.target.value)}
                style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
                NotArb макс. спам %
              </label>
              <input
                type="number"
                step="1"
                min="0"
                max="100"
                value={vals['notarb_max_spam_percentage'] || '50'}
                onChange={(e) => update('notarb_max_spam_percentage', e.target.value)}
                style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
              />
              <small style={{ color: '#666' }}>
                Максимальный процент спама для экспорта в NotArb (0-100)
              </small>
            </div>
          </div>
          
          <div style={{ marginTop: 16 }}>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
              🤖 Whitelist кошельков (игнорировать в спам-анализе)
            </label>
            <textarea
              value={vals['spam_whitelist_wallets'] || '8vNwSvT1S8P99c9XmjfXfV4DSGZLfUoNFx63zngCuh54'}
              onChange={(e) => update('spam_whitelist_wallets', e.target.value)}
              style={{ 
                width: '100%', 
                padding: 8, 
                border: '1px solid #ccc', 
                borderRadius: 4,
                fontFamily: 'monospace',
                fontSize: '12px',
                minHeight: '60px'
              }}
              placeholder="Адреса кошельков через запятую"
            />
            <small style={{ color: '#666' }}>
              Кошельки ботов и доверенных источников (через запятую). Их транзакции не учитываются при подсчете спама.
            </small>
          </div>
        </div>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h3>🔍 Мониторинг backlog</h3>
        <div style={{ background: 'white', padding: 16, borderRadius: 8, border: '1px solid #dee2e6' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 16 }}>
            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
                ⚠️ Порог предупреждения
              </label>
              <input
                type="number"
                step="5"
                min="10"
                max="500"
                value={vals['backlog_warning_threshold'] || '75'}
                onChange={(e) => update('backlog_warning_threshold', e.target.value)}
                style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
              />
              <small style={{ color: '#666' }}>
                Размер backlog для предупреждения
              </small>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
                🚨 Порог ошибки
              </label>
              <input
                type="number"
                step="5"
                min="20"
                max="500"
                value={vals['backlog_error_threshold'] || '100'}
                onChange={(e) => update('backlog_error_threshold', e.target.value)}
                style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
              />
              <small style={{ color: '#666' }}>
                Размер backlog для алерта об ошибке
              </small>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
                🔥 Критический порог
              </label>
              <input
                type="number"
                step="10"
                min="50"
                max="500"
                value={vals['backlog_critical_threshold'] || '150'}
                onChange={(e) => update('backlog_critical_threshold', e.target.value)}
                style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
              />
              <small style={{ color: '#666' }}>
                Размер backlog для критического алерта
              </small>
            </div>
          </div>
        </div>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h3>📦 Параметры архивации</h3>
        <div style={{ background: 'white', padding: 16, borderRadius: 8, border: '1px solid #dee2e6' }}>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 16 }}>
            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
                📦 Архив активных (часы)
              </label>
              <input
                type="number"
                step="1"
                min="1"
                max="72"
                value={vals['archive_below_hours'] || '12'}
                onChange={(e) => update('archive_below_hours', e.target.value)}
                style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
              />
              <small style={{ color: '#666' }}>
                Через сколько часов архивировать активные токены с низким скором.
              </small>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
                ⏰ Таймаут мониторинга (часы)
              </label>
              <input
                type="number"
                step="1"
                min="1"
                max="72"
                value={vals['monitoring_timeout_hours'] || '12'}
                onChange={(e) => update('monitoring_timeout_hours', e.target.value)}
                style={{ width: '100%', padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
              />
              <small style={{ color: '#666' }}>
                Через сколько часов архивировать токены в мониторинге.
              </small>
            </div>
          </div>
        </div>
      </section>

      <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
        <button
          onClick={() => save(false)}
          disabled={saving}
          style={{
            padding: '12px 24px',
            background: '#28a745',
            color: 'white',
            border: 'none',
            borderRadius: 4,
            cursor: saving ? 'not-allowed' : 'pointer',
            opacity: saving ? 0.6 : 1
          }}
        >
          {saving ? 'Сохранение...' : 'Сохранить'}
        </button>
        
        <button
          onClick={() => save(true)}
          disabled={saving}
          style={{
            padding: '12px 24px',
            background: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: 4,
            cursor: saving ? 'not-allowed' : 'pointer',
            opacity: saving ? 0.6 : 1
          }}
        >
          {saving ? 'Сохранение...' : 'Сохранить и пересчитать'}
        </button>
      </div>
    </div>
  )
}