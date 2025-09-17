import { useEffect, useState } from 'react'
import { getDefaultSettings, getSettings, putSetting, recalc, SettingsMap, getActiveModel, switchModel } from '../lib/api'

const legacyKeys = [
  'weight_s','weight_l','weight_m','weight_t',
  'min_score','score_smoothing_alpha','min_pool_liquidity_usd','max_price_change_5m','min_score_change','max_liquidity_change_ratio',
  'hot_interval_sec','cold_interval_sec','archive_below_hours','monitoring_timeout_hours',
  'activation_min_liquidity_usd'
]

const hybridKeys = [
  'w_tx','w_vol','w_fresh','w_oi',
  'ewma_alpha','freshness_threshold_hours',
  'min_score','min_pool_liquidity_usd','max_price_change_5m','min_score_change','max_liquidity_change_ratio',
  'hot_interval_sec','cold_interval_sec','archive_below_hours','monitoring_timeout_hours',
  'activation_min_liquidity_usd'
]

function getSettingsKeys(model: string): string[] {
  return model === 'hybrid_momentum' ? hybridKeys : legacyKeys
}

export default function Settings(){
  const [vals, setVals] = useState<SettingsMap>({})
  const [activeModel, setActiveModel] = useState<string>('legacy')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string>('')

  useEffect(()=>{ (async()=>{
    setLoading(true)
    try{ 
      const [settings, model] = await Promise.all([getSettings(), getActiveModel()])
      setVals(settings)
      setActiveModel(model)
    } finally{ setLoading(false) }
  })() }, [])

  const update = (k: string, v: string) => setVals(prev=>({...prev, [k]: v}))

  async function save(recalculate: boolean){
    setSaving(true); setMessage('')
    try{
      const keys = getSettingsKeys(activeModel)
      for(const k of keys){
        if(vals[k] != null){ await putSetting(k, String(vals[k])) }
      }
      if(recalculate){ await recalc() }
      setMessage(recalculate ? 'Сохранено. Пересчёт запущен.' : 'Сохранено.')
    } finally{ setSaving(false) }
  }

  async function handleModelSwitch(newModel: string){
    if(newModel === activeModel) return
    setSaving(true); setMessage('')
    try{
      await switchModel(newModel)
      setActiveModel(newModel)
      // Reload settings for new model
      const settings = await getSettings()
      setVals(settings)
      setMessage(`Переключено на модель: ${newModel === 'hybrid_momentum' ? 'Hybrid Momentum' : 'Legacy'}`)
    } catch(e) {
      setMessage('Ошибка переключения модели')
    } finally{ setSaving(false) }
  }

  async function resetDefaults(){
    try{
      const defs = await getDefaultSettings()
      setVals(defs)
      setMessage('Загружены дефолтные значения (не сохранены). Нажмите Сохранить.')
    }catch(e){ setMessage('Не удалось загрузить дефолты') }
  }

  return (
    <div>
      <h2>Настройки</h2>
      {loading ? <p>Загрузка...</p> : (
        <div className="settings">
          <ModelSelector 
            activeModel={activeModel} 
            onModelChange={handleModelSwitch} 
            disabled={saving} 
          />
          <section>
            <h3>Весовые коэффициенты</h3>
            {activeModel === 'hybrid_momentum' ? (
              <>
                <Field label="Вес ускорения транзакций (w_tx)" type="number" hint="Измеряет изменения скорости транзакций - ускорение/замедление активности" k="w_tx" v={vals['w_tx']} set={update} />
                <Field label="Вес моментума объёма (w_vol)" type="number" hint="Отслеживает ускорение трендов объёма торгов" k="w_vol" v={vals['w_vol']} set={update} />
                <Field label="Вес свежести токена (w_fresh)" type="number" hint="Поощряет недавно созданные токены (первые 6 часов)" k="w_fresh" v={vals['w_fresh']} set={update} />
                <Field label="Вес дисбаланса ордерфлоу (w_oi)" type="number" hint="Измеряет дисбаланс давления покупок/продаж" k="w_oi" v={vals['w_oi']} set={update} />
                <WeightsSum ws={vals['w_tx']} wl={vals['w_vol']} wm={vals['w_fresh']} wt={vals['w_oi']} />
              </>
            ) : (
              <>
                <Field label="Вес волатильности (W_s)" type="number" hint="Определяет важность краткосрочной активности цены" k="weight_s" v={vals['weight_s']} set={update} />
                <Field label="Вес ликвидности (W_l)" type="number" hint="Отражает устойчивость актива и глубину рынка" k="weight_l" v={vals['weight_l']} set={update} />
                <Field label="Вес импульса (W_m)" type="number" hint="Соотношение движений 5м/15м для выявления импульса" k="weight_m" v={vals['weight_m']} set={update} />
                <Field label="Вес частоты торгов (W_t)" type="number" hint="Число сделок как прокси интереса трейдеров" k="weight_t" v={vals['weight_t']} set={update} />
                <WeightsSum ws={vals['weight_s']} wl={vals['weight_l']} wm={vals['weight_m']} wt={vals['weight_t']} />
              </>
            )}
            <Formula activeModel={activeModel} vals={vals} />
          </section>
          <section>
            <h3>Пороги</h3>
            <Field label="Минимальное значение скора (τ)" type="number" hint="Токены ниже порога не отображаются на дашборде" k="min_score" v={vals['min_score']} set={update} />
          </section>
          {activeModel === 'hybrid_momentum' ? (
            <section>
              <h3>🚀 Hybrid Momentum настройки</h3>
              <Field 
                label="EWMA коэффициент (α)" 
                type="number" 
                hint="Сглаживание компонентов: 0.1 = сильное сглаживание, 0.3 = баланс (рекомендуется), 0.5 = быстрая адаптация" 
                k="ewma_alpha" 
                v={vals['ewma_alpha']} 
                set={update} 
              />
              <Field 
                label="Порог свежести токена (часы)" 
                type="number" 
                hint="Время в часах, в течение которого токен считается 'свежим' и получает бонус к скору" 
                k="freshness_threshold_hours" 
                v={vals['freshness_threshold_hours']} 
                set={update} 
              />
              <HybridMomentumHelp alpha={vals['ewma_alpha']} freshness={vals['freshness_threshold_hours']} />
            </section>
          ) : (
            <section>
              <h3>Сглаживание скоров</h3>
              <Field 
                label="Коэффициент сглаживания (α)" 
                type="number" 
                hint="Экспоненциальное скользящее среднее: 0.1 = сильное сглаживание, 0.3 = баланс (рекомендуется), 0.5 = быстрая адаптация, 1.0 = без сглаживания" 
                k="score_smoothing_alpha" 
                v={vals['score_smoothing_alpha']} 
                set={update} 
              />
              <SmoothingHelp alpha={vals['score_smoothing_alpha']} />
            </section>
          )}
          <section>
            <h3>Фильтрация данных</h3>
            <Field 
              label="Мин. ликвидность пула (USD)" 
              type="number" 
              hint="Пулы с ликвидностью ниже этого значения игнорируются (фильтрация пылинок)" 
              k="min_pool_liquidity_usd" 
              v={vals['min_pool_liquidity_usd']} 
              set={update} 
            />
            <Field 
              label="Макс. изменение цены за 5м (%)" 
              type="number" 
              hint="Изменения цены выше этого значения считаются аномалиями и ограничиваются" 
              k="max_price_change_5m" 
              v={vals['max_price_change_5m']} 
              set={update} 
            />
            <Field 
              label="Мин. изменение скора для обновления" 
              type="number" 
              hint="Изменения скора меньше этого значения игнорируются (снижение шума)" 
              k="min_score_change" 
              v={vals['min_score_change']} 
              set={update} 
            />
            <Field 
              label="Макс. изменение ликвидности (коэффициент)" 
              type="number" 
              hint="Максимальное отношение изменения ликвидности за одно обновление (защита от резких скачков)" 
              k="max_liquidity_change_ratio" 
              v={vals['max_liquidity_change_ratio']} 
              set={update} 
            />
            <DataFilteringHelp />
          </section>
          <section>
            <h3>Тайминги и жизненный цикл</h3>
            <Field label="Интервал для горячих (сек)" type="number" hint="Статус: active с последним скором ≥ τ (min_score). Частота обновлений метрик/скора для таких токенов." k="hot_interval_sec" v={vals['hot_interval_sec']} set={update} />
            <Field label="Интервал для остывших (сек)" type="number" hint="Статус: active с последним скором < τ либо без скора. Обновляются реже, чтобы экономить лимиты." k="cold_interval_sec" v={vals['cold_interval_sec']} set={update} />
            <Field label="Период неактивности для архивации (час)" type="number" hint="Статус: active → archived, если в течение этого периода ни разу не было скора ≥ τ." k="archive_below_hours" v={vals['archive_below_hours']} set={update} />
            <Field label="Таймаут мониторинга (час)" type="number" hint="Статус: monitoring → archived, если за этот период не выполнены условия активации." k="monitoring_timeout_hours" v={vals['monitoring_timeout_hours']} set={update} />
            <Field label="Мин. ликвидность внешнего пула для активации (USD)" type="number" hint="Статусы: monitoring↔active. Активируем при наличии внешнего пула WSOL/SOL/USDC (не pumpfun/pumpswap/pumpfun-amm) с ликвидностью ≥ порога; при отсутствии — возвращаем в monitoring." k="activation_min_liquidity_usd" v={vals['activation_min_liquidity_usd']} set={update} />
          </section>
          <div className="actions">
            <button disabled={saving} onClick={()=>save(false)}>{saving? 'Сохранение...' : 'Сохранить'}</button>
            <button disabled={saving} onClick={()=>save(true)}>{saving? '...' : 'Сохранить и Пересчитать'}</button>
            <button disabled={saving} onClick={resetDefaults}>Сбросить к дефолту</button>
            {message && <span className="muted" style={{marginLeft: 8}}>{message}</span>}
          </div>
        </div>
      )}
    </div>
  )
}

function Field({label, hint, k, v, set, type}:{label:string, hint?:string, k:string,v?:string,set:(k:string,v:string)=>void, type?: 'number'|'text'}){
  return (
    <label className="field" title={hint}>
      <span>{label}</span>
      <input value={v??''} onChange={e=>set(k, e.target.value)} title={hint} type={type||'text'} step={type==='number'? '0.01' : undefined} />
    </label>
  )
}

function Formula({activeModel, vals}:{activeModel:string, vals:SettingsMap}){
  return (
    <div style={{marginTop:8}}>
      <h4 style={{margin:'8px 0'}}>Формула скоринга</h4>
      {activeModel === 'hybrid_momentum' ? <HybridMomentumFormula vals={vals} /> : <LegacyFormula />}
    </div>
  )
}

function HybridMomentumFormula({vals}:{vals:SettingsMap}){
  return (
    <pre style={{whiteSpace:'pre-wrap', background:'#f0f8ff', border:'2px solid #4a90e2', padding:12, borderRadius:6}}>
🚀 <strong>Hybrid Momentum Model</strong>

S = w_tx·TX_accel + w_vol·VOL_momentum + w_fresh·TOKEN_freshness + w_oi·OI_imbalance

<strong>Компоненты:</strong>
• TX_accel = EWMA(tx_count_5m / tx_count_1h * 12) - ускорение транзакций
• VOL_momentum = EWMA(volume_5m / volume_1h * 12) - моментум объёма  
• TOKEN_freshness = max(0, 1 - hours_since_creation / 6) - свежесть токена
• OI_imbalance = |buys_volume - sells_volume| / total_volume - дисбаланс ордерфлоу

<strong>EWMA сглаживание:</strong>
smoothed = α × new_value + (1-α) × previous_smoothed
где α = {vals['ewma_alpha'] || '0.3'} (коэффициент сглаживания)

<strong>Преимущества:</strong>
✅ Учитывает динамику изменений (ускорение/замедление)
✅ Поощряет свежие токены в первые 6 часов
✅ Измеряет дисбаланс покупок/продаж
✅ EWMA сглаживание снижает шум на 25-40%
    </pre>
  )
}

function LegacyFormula(){
  return (
    <pre style={{whiteSpace:'pre-wrap', background:'#fafafa', border:'1px solid #eee', padding:8, borderRadius:4}}>
📊 <strong>Legacy Model</strong>

S = HD_norm · (W_s·s + W_l·l + W_m·m + W_t·t)

где:
- l = clip((log10(L_tot) − 4) / 2)
- s = clip(log(1 + |ΔP_5m| × 10) / log(11))  📈 исправлено
- m = clip(|ΔP_5м| / max(|ΔP_15м|, 0.01))     🔧 исправлено  
- t = clip((N_5м / 5) / 300)
- clip(x) = min(max(x, 0), 1)

Исправления волатильности:
- s: логарифмическое сглаживание вместо линейного деления
- m: защита от деления на очень малые числа

Примечания:
- L_tot — суммарная ликвидность по WSOL/SOL/USDC пулам (без classic pumpfun).
- ΔP берётся по самой ликвидной паре; если m15 отсутствует, используется h1/4.
- N_5м — сумма (buys+sells) за 5 минут по всем учтённым пулам.
- Скоры дополнительно сглажены через экспоненциальное скользящее среднее.
    </pre>
  )
}

function WeightsSum({ws, wl, wm, wt}:{ws?:string, wl?:string, wm?:string, wt?:string}){
  let sum = 0
  try{ sum = (parseFloat(ws||'0')||0) + (parseFloat(wl||'0')||0) + (parseFloat(wm||'0')||0) + (parseFloat(wt||'0')||0) }catch{}
  const ok = Math.abs(sum - 1) <= 0.05
  return <div className="muted">ΣW ≈ {sum.toFixed(2)} {ok? '' : ' (внимание: рекомендуется ≈ 1.00)'}</div>
}

function SmoothingHelp({alpha}:{alpha?:string}){
  const a = parseFloat(alpha || '0.3')
  const isValid = a >= 0 && a <= 1
  
  let description = ''
  if (!isValid) {
    description = '❌ Значение должно быть от 0.0 до 1.0'
  } else if (a <= 0.1) {
    description = '🐌 Максимальное сглаживание, очень медленная адаптация'
  } else if (a <= 0.3) {
    description = '✅ Оптимальный баланс (рекомендуется)'
  } else if (a <= 0.5) {
    description = '⚡ Быстрая адаптация, умеренное сглаживание'
  } else if (a < 1.0) {
    description = '🏃 Минимальное сглаживание'
  } else {
    description = '🚫 Без сглаживания (как было раньше)'
  }
  
  return (
    <div style={{marginTop: 8}}>
      <div className="muted" style={{fontSize: '0.9em'}}>
        {description}
      </div>
      <div style={{marginTop: 4, fontSize: '0.85em', color: '#666'}}>
        Формула: smoothed = {a.toFixed(1)} × new + {(1-a).toFixed(1)} × previous
      </div>
    </div>
  )
}

function DataFilteringHelp(){
  return (
    <div style={{marginTop: 8, padding: 8, background: '#f8f9fa', border: '1px solid #dee2e6', borderRadius: 4}}>
      <h4 style={{margin: '0 0 8px 0', fontSize: '0.9em'}}>🛡️ Фильтрация данных</h4>
      <div style={{fontSize: '0.85em', color: '#666'}}>
        <div><strong>Цель:</strong> Устранение аномалий и шума в данных для стабилизации скоров</div>
        <div style={{marginTop: 4}}>
          <strong>Эффекты:</strong>
          <ul style={{margin: '4px 0', paddingLeft: 16}}>
            <li>🧹 Фильтрация пулов-пылинок (&lt; $500)</li>
            <li>🚫 Блокировка экстремальных изменений цены (&gt; 50%)</li>
            <li>🔇 Игнорирование незначительного шума (&lt; 5%)</li>
            <li>⚡ Сглаживание резких скачков ликвидности</li>
          </ul>
        </div>
        <div style={{marginTop: 4, fontStyle: 'italic'}}>
          Ожидаемый эффект: дополнительное снижение волатильности на 15-25%
        </div>
      </div>
    </div>
  )
}

function ModelSelector({activeModel, onModelChange, disabled}:{activeModel:string, onModelChange:(model:string)=>void, disabled:boolean}){
  return (
    <section style={{marginBottom: 20, padding: 12, background: '#f0f8ff', border: '2px solid #4a90e2', borderRadius: 6}}>
      <h3 style={{margin: '0 0 12px 0', color: '#2c5aa0'}}>🎯 Модель скоринга</h3>
      <div style={{display: 'flex', alignItems: 'center', gap: 12}}>
        <label style={{fontWeight: 'bold'}}>Активная модель:</label>
        <select 
          value={activeModel} 
          onChange={e => onModelChange(e.target.value)}
          disabled={disabled}
          style={{padding: '6px 12px', borderRadius: 4, border: '1px solid #ccc', fontSize: '14px'}}
        >
          <option value="legacy">Legacy (Классическая)</option>
          <option value="hybrid_momentum">Hybrid Momentum (Новая)</option>
        </select>
        <div style={{fontSize: '0.9em', color: '#666', marginLeft: 8}}>
          {activeModel === 'hybrid_momentum' ? 
            '🚀 4-компонентная модель с EWMA сглаживанием' : 
            '📊 Классическая модель скоринга'
          }
        </div>
      </div>
    </section>
  )
}

function HybridMomentumHelp({alpha, freshness}:{alpha?:string, freshness?:string}){
  const a = parseFloat(alpha || '0.3')
  const f = parseFloat(freshness || '6.0')
  
  return (
    <div style={{marginTop: 8, padding: 8, background: '#f0f8ff', border: '1px solid #4a90e2', borderRadius: 4}}>
      <h4 style={{margin: '0 0 8px 0', fontSize: '0.9em'}}>🚀 Hybrid Momentum параметры</h4>
      <div style={{fontSize: '0.85em', color: '#666'}}>
        <div><strong>EWMA α = {a.toFixed(2)}:</strong> {
          a <= 0.1 ? '🐌 Максимальное сглаживание' :
          a <= 0.3 ? '✅ Оптимальный баланс' :
          a <= 0.5 ? '⚡ Быстрая адаптация' : '🏃 Минимальное сглаживание'
        }</div>
        <div style={{marginTop: 4}}>
          <strong>Свежесть = {f.toFixed(1)}ч:</strong> Токены получают бонус в первые {f.toFixed(1)} часов после создания
        </div>
        <div style={{marginTop: 4}}>
          <strong>Компоненты:</strong>
          <ul style={{margin: '4px 0', paddingLeft: 16}}>
            <li>🔥 TX Acceleration - ускорение транзакций</li>
            <li>📈 Volume Momentum - моментум объёма</li>
            <li>🆕 Token Freshness - свежесть токена</li>
            <li>⚖️ Orderflow Imbalance - дисбаланс ордерфлоу</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
