import { useEffect, useState } from 'react'
import { getDefaultSettings, getSettings, getSettingsIndividually, putSetting, recalc, SettingsMap, getActiveModel, switchModel } from '../lib/api'

const legacyKeys = [
  'weight_s','weight_l','weight_m','weight_t',
  'score_smoothing_alpha',
  'min_score',
  'min_pool_liquidity_usd',
  'hot_interval_sec','cold_interval_sec',
  'archive_below_hours','monitoring_timeout_hours',
  'activation_min_liquidity_usd',
  'notarb_min_score'
]

const hybridKeys = [
  'w_tx','w_vol','w_fresh','w_oi',
  'ewma_alpha','freshness_threshold_hours',
  'min_score',
  'min_pool_liquidity_usd',
  'hot_interval_sec','cold_interval_sec',
  'archive_below_hours','monitoring_timeout_hours',
  'activation_min_liquidity_usd',
  'notarb_min_score'
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
      const model = await getActiveModel()
      setActiveModel(model)
      
      // Load settings individually to avoid /settings/ timeout
      const keys = getSettingsKeys(model)
      const settings = await getSettingsIndividually(keys)
      setVals(settings)
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
      const keys = getSettingsKeys(newModel)
      const settings = await getSettingsIndividually(keys)
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
      <h2>Настройки системы скоринга</h2>
      {loading ? <p>Загрузка...</p> : (
        <div className="settings">
          <TokenLifecycleAlgorithm />
          <ModelSelector 
            activeModel={activeModel} 
            onModelChange={handleModelSwitch} 
            disabled={saving} 
          />
          <section>
            <h3>Весовые коэффициенты модели скоринга</h3>
            {activeModel === 'hybrid_momentum' ? (
              <>
                <Field label="Вес ускорения транзакций (w_tx)" type="number" hint="Что это: Важность компонента TX Acceleration в итоговом скоре. Измеряет ускорение/замедление транзакционной активности токена за последние 5 минут относительно часового тренда." k="w_tx" v={vals['w_tx']} set={update} />
                <Field label="Вес моментума объёма (w_vol)" type="number" hint="Что это: Важность компонента Volume Momentum в итоговом скоре. Отслеживает ускорение трендов торгового объёма - растет ли интерес к токену или угасает." k="w_vol" v={vals['w_vol']} set={update} />
                <Field label="Вес свежести токена (w_fresh)" type="number" hint="Что это: Важность компонента Token Freshness в итоговом скоре. Даёт бонус недавно созданным токенам (первые 6 часов после миграции с Pump.fun) для раннего обнаружения возможностей." k="w_fresh" v={vals['w_fresh']} set={update} />
                <Field label="Вес дисбаланса ордерфлоу (w_oi)" type="number" hint="Что это: Важность компонента Orderflow Imbalance в итоговом скоре. Измеряет дисбаланс между объёмами покупок и продаж - преобладает ли давление покупателей или продавцов." k="w_oi" v={vals['w_oi']} set={update} />
                <WeightsSum ws={vals['w_tx']} wl={vals['w_vol']} wm={vals['w_fresh']} wt={vals['w_oi']} />
              </>
            ) : (
              <>
                <Field label="Вес волатильности (W_s)" type="number" hint="Что это: Важность ценовой волатильности в итоговом скоре. Определяет, насколько сильно краткосрочные изменения цены (за 5 минут) влияют на оценку токена." k="weight_s" v={vals['weight_s']} set={update} />
                <Field label="Вес ликвидности (W_l)" type="number" hint="Что это: Важность общей ликвидности токена в итоговом скоре. Отражает глубину рынка и возможность торговать без значительного слиппажа." k="weight_l" v={vals['weight_l']} set={update} />
                <Field label="Вес импульса (W_m)" type="number" hint="Что это: Важность ценового импульса в итоговом скоре. Сравнивает изменения цены за 5 и 15 минут для выявления ускорения или замедления движения." k="weight_m" v={vals['weight_m']} set={update} />
                <Field label="Вес частоты торгов (W_t)" type="number" hint="Что это: Важность транзакционной активности в итоговом скоре. Учитывает количество сделок за 5 минут как показатель интереса трейдеров к токену." k="weight_t" v={vals['weight_t']} set={update} />
                <WeightsSum ws={vals['weight_s']} wl={vals['weight_l']} wm={vals['weight_m']} wt={vals['weight_t']} />
              </>
            )}
            <Formula activeModel={activeModel} vals={vals} />
          </section>
          {activeModel === 'hybrid_momentum' ? (
            <section>
              <h3>🚀 Параметры сглаживания</h3>
              <Field 
                label="EWMA коэффициент (α)" 
                type="number" 
                hint="Что это: Параметр экспоненциального скользящего среднего для сглаживания всех компонентов скоринга. Контролирует баланс между стабильностью (низкие значения) и отзывчивостью (высокие значения). 0.1 = максимальная стабильность, 0.3 = оптимальный баланс, 0.5 = быстрая реакция на изменения." 
                k="ewma_alpha" 
                v={vals['ewma_alpha']} 
                set={update} 
              />
              <Field 
                label="Порог свежести токена (часы)" 
                type="number" 
                hint="Что это: Временное окно в часах, в течение которого токен считается 'свежим' после миграции с Pump.fun. В этот период токен получает максимальный бонус по компоненту Token Freshness, который линейно уменьшается до нуля." 
                k="freshness_threshold_hours" 
                v={vals['freshness_threshold_hours']} 
                set={update} 
              />
              <HybridMomentumHelp alpha={vals['ewma_alpha']} freshness={vals['freshness_threshold_hours']} />
            </section>
          ) : (
            <section>
              <h3>📊 Параметры сглаживания</h3>
              <Field 
                label="Коэффициент сглаживания (α)" 
                type="number" 
                hint="Что это: Параметр экспоненциального скользящего среднего для сглаживания итогового скора токена. Уменьшает волатильность скоров, фильтруя кратковременные колебания. 0.1 = максимальная стабильность (медленная реакция), 0.3 = оптимальный баланс, 0.5 = быстрая адаптация к изменениям." 
                k="score_smoothing_alpha" 
                v={vals['score_smoothing_alpha']} 
                set={update} 
              />
              <SmoothingHelp alpha={vals['score_smoothing_alpha']} />
            </section>
          )}
          <section>
            <h3>⚙️ Параметры алгоритма</h3>
            <Field 
              label="Минимальный скор для отображения" 
              type="number" 
              hint="Что это: Пороговое значение скора для фильтрации токенов в дашборде (этап 6 алгоритма). Токены с скором ниже этого значения скрываются из основного списка, позволяя сосредоточиться только на перспективных возможностях." 
              k="min_score" 
              v={vals['min_score']} 
              set={update} 
            />
            <Field 
              label="Минимальная ликвидность пула (USD)" 
              type="number" 
              hint="Что это: Минимальная ликвидность пула для включения в расчеты метрик (этап 3 алгоритма). Пулы с меньшей ликвидностью считаются 'пылинками' и игнорируются, что повышает точность расчетов и исключает шум от мелких пулов." 
              k="min_pool_liquidity_usd" 
              v={vals['min_pool_liquidity_usd']} 
              set={update} 
            />
            {/* NOTE: max_price_change_5m field removed - not used in Hybrid Momentum model */}
            <Field 
              label="Минимальная ликвидность для активации (USD)" 
              type="number" 
              hint="Что это: Минимальная ликвидность внешнего пула для перехода токена из статуса 'мониторинг' в 'активный' (этап 2 алгоритма). Токен активируется только при наличии серьезного внешнего пула (не Pump.fun), что гарантирует реальную торговую активность." 
              k="activation_min_liquidity_usd" 
              v={vals['activation_min_liquidity_usd']} 
              set={update} 
            />
          </section>
          <section>
            <h3>🤖 NotArb Bot Integration</h3>
            <Field 
              label="Минимальный скор для NotArb бота" 
              type="number" 
              hint="Что это: Минимальный скор токена для включения в конфигурацию NotArb бота. Только токены с скором выше этого значения будут экспортированы в markets.json для арбитражного бота. Рекомендуется значение 0.5-1.0 для фильтрации только перспективных токенов." 
              k="notarb_min_score" 
              v={vals['notarb_min_score']} 
              set={update} 
            />
          </section>
          <section>
            <h3>⏱️ Временные интервалы</h3>
            <Field 
              label="Интервал обновления активных токенов (сек)" 
              type="number" 
              hint="Что это: Частота пересчета скоров для 'горячих' токенов с высоким потенциалом (этап 4-5 алгоритма). Активные токены с хорошим скором обновляются чаще для быстрого реагирования на изменения рынка." 
              k="hot_interval_sec" 
              v={vals['hot_interval_sec']} 
              set={update} 
            />
            <Field 
              label="Интервал обновления неактивных токенов (сек)" 
              type="number" 
              hint="Что это: Частота пересчета скоров для 'остывших' токенов с низким скором. Такие токены обновляются реже для экономии вычислительных ресурсов и лимитов внешних API, но продолжают отслеживаться на случай восстановления активности." 
              k="cold_interval_sec" 
              v={vals['cold_interval_sec']} 
              set={update} 
            />
            <Field 
              label="Время до архивации активных токенов (час)" 
              type="number" 
              hint="Что это: Период неактивности в часах, после которого активные токены переводятся в архив (этап 7 алгоритма). Если токен не показывает скор выше минимального порога в течение этого времени, он считается неперспективным и архивируется для экономии ресурсов." 
              k="archive_below_hours" 
              v={vals['archive_below_hours']} 
              set={update} 
            />
            <Field 
              label="Время до архивации мониторинга (час)" 
              type="number" 
              hint="Что это: Максимальное время в часах, которое токен может находиться в статусе 'мониторинг' (этап 7 алгоритма). Если за это время токен не активируется (не появляется внешний пул с достаточной ликвидностью), он архивируется как неперспективный." 
              k="monitoring_timeout_hours" 
              v={vals['monitoring_timeout_hours']} 
              set={update} 
            />
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
  const wTx = vals['w_tx'] || '0.25'
  const wVol = vals['w_vol'] || '0.25'
  const wFresh = vals['w_fresh'] || '0.25'
  const wOi = vals['w_oi'] || '0.25'
  const alpha = vals['ewma_alpha'] || '0.3'
  const freshness = vals['freshness_threshold_hours'] || '6.0'
  
  return (
    <div style={{background:'#f0f8ff', border:'2px solid #4a90e2', padding:16, borderRadius:8, marginTop: 12}}>
      <h4 style={{margin: '0 0 12px 0', color: '#2c5aa0'}}>🚀 Hybrid Momentum Model</h4>
      
      <div style={{background: 'white', padding: 12, borderRadius: 6, marginBottom: 12, fontFamily: 'monospace', fontSize: '0.9em'}}>
        <strong>Итоговая формула:</strong><br/>
        Score = {wTx}×TX + {wVol}×Vol + {wFresh}×Fresh + {wOi}×OI
      </div>

      <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 12, marginBottom: 12}}>
        <div style={{background: 'white', padding: 10, borderRadius: 4, border: '1px solid #dee2e6'}}>
          <strong>🔥 TX Acceleration</strong><br/>
          <span style={{fontSize: '0.85em', color: '#666'}}>
            Ускорение транзакций<br/>
            tx_5m / (tx_1h / 12)
          </span>
        </div>
        
        <div style={{background: 'white', padding: 10, borderRadius: 4, border: '1px solid #dee2e6'}}>
          <strong>📈 Volume Momentum</strong><br/>
          <span style={{fontSize: '0.85em', color: '#666'}}>
            Импульс объема<br/>
            vol_5m / (vol_1h / 12)
          </span>
        </div>
        
        <div style={{background: 'white', padding: 10, borderRadius: 4, border: '1px solid #dee2e6'}}>
          <strong>🆕 Token Freshness</strong><br/>
          <span style={{fontSize: '0.85em', color: '#666'}}>
            Свежесть токена<br/>
            max(0, 1 - hours/{freshness})
          </span>
        </div>
        
        <div style={{background: 'white', padding: 10, borderRadius: 4, border: '1px solid #dee2e6'}}>
          <strong>⚖️ Orderflow Imbalance</strong><br/>
          <span style={{fontSize: '0.85em', color: '#666'}}>
            Дисбаланс ордеров<br/>
            |buys - sells| / total
          </span>
        </div>
      </div>

      <div style={{background: '#e3f2fd', padding: 10, borderRadius: 4, border: '1px solid #90caf9'}}>
        <strong>🔧 EWMA Сглаживание (α = {alpha}):</strong><br/>
        <span style={{fontSize: '0.9em'}}>
          smoothed = {alpha} × новое_значение + {(1 - parseFloat(alpha)).toFixed(1)} × предыдущее_сглаженное<br/>
          <em>Снижает шум и ложные сигналы на 25-40%</em>
        </span>
      </div>
    </div>
  )
}

function LegacyFormula(){
  return (
    <div style={{background:'#fafafa', border:'1px solid #ddd', padding:16, borderRadius:8, marginTop: 12}}>
      <h4 style={{margin: '0 0 12px 0', color: '#495057'}}>📊 Legacy Model</h4>
      
      <div style={{background: 'white', padding: 12, borderRadius: 6, marginBottom: 12, fontFamily: 'monospace', fontSize: '0.9em'}}>
        <strong>Итоговая формула:</strong><br/>
        Score = W_s×s + W_l×l + W_m×m + W_t×t
      </div>

      <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 12}}>
        <div style={{background: 'white', padding: 10, borderRadius: 4, border: '1px solid #dee2e6'}}>
          <strong>📈 Волатильность (s)</strong><br/>
          <span style={{fontSize: '0.85em', color: '#666'}}>
            Краткосрочная активность<br/>
            log(1 + |ΔP_5m| × 10) / log(11)
          </span>
        </div>
        
        <div style={{background: 'white', padding: 10, borderRadius: 4, border: '1px solid #dee2e6'}}>
          <strong>💰 Ликвидность (l)</strong><br/>
          <span style={{fontSize: '0.85em', color: '#666'}}>
            Глубина рынка<br/>
            (log10(L_tot) − 4) / 2
          </span>
        </div>
        
        <div style={{background: 'white', padding: 10, borderRadius: 4, border: '1px solid #dee2e6'}}>
          <strong>⚡ Импульс (m)</strong><br/>
          <span style={{fontSize: '0.85em', color: '#666'}}>
            Соотношение 5м/15м<br/>
            |ΔP_5м| / max(|ΔP_15м|, 0.01)
          </span>
        </div>
        
        <div style={{background: 'white', padding: 10, borderRadius: 4, border: '1px solid #dee2e6'}}>
          <strong>🔄 Транзакции (t)</strong><br/>
          <span style={{fontSize: '0.85em', color: '#666'}}>
            Частота торгов<br/>
            (N_5м / 5) / 300
          </span>
        </div>
      </div>

      <div style={{background: '#fff3cd', padding: 10, borderRadius: 4, border: '1px solid #ffeaa7'}}>
        <strong>📝 Особенности:</strong><br/>
        <span style={{fontSize: '0.9em'}}>
          • Все компоненты нормализованы в диапазон [0, 1]<br/>
          • Логарифмическое сглаживание волатильности<br/>
          • Защита от деления на малые числа<br/>
          • Дополнительное EWMA сглаживание итогового скора
        </span>
      </div>
    </div>
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

function TokenLifecycleAlgorithm(){
  return (
    <section style={{marginBottom: 24, padding: 16, background: '#f8f9fa', border: '2px solid #28a745', borderRadius: 8}}>
      <h3 style={{margin: '0 0 16px 0', color: '#155724', display: 'flex', alignItems: 'center', gap: 8}}>
        🔄 Алгоритм жизненного цикла токенов
      </h3>
      
      <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16}}>
        
        <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #dee2e6'}}>
          <h4 style={{margin: '0 0 8px 0', color: '#007bff'}}>1️⃣ Обнаружение токенов</h4>
          <div style={{fontSize: '0.9em', lineHeight: 1.4}}>
            <strong>WebSocket подписка на Pump.fun:</strong><br/>
            • Отслеживаем миграции токенов с Pump.fun<br/>
            • Создаем запись со статусом <code>monitoring</code><br/>
            • Начинаем отслеживание токена
          </div>
        </div>

        <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #dee2e6'}}>
          <h4 style={{margin: '0 0 8px 0', color: '#28a745'}}>2️⃣ Активация токена</h4>
          <div style={{fontSize: '0.9em', lineHeight: 1.4}}>
            <strong>Проверка через DexScreener:</strong><br/>
            • Ищем внешние пулы (не Pump.fun)<br/>
            • Если ликвидность ≥ порога → статус <code>active</code><br/>
            • Если нет внешних пулов → остается <code>monitoring</code>
          </div>
        </div>

        <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #dee2e6'}}>
          <h4 style={{margin: '0 0 8px 0', color: '#ffc107'}}>3️⃣ Сбор метрик</h4>
          <div style={{fontSize: '0.9em', lineHeight: 1.4}}>
            <strong>Агрегация данных по пулам:</strong><br/>
            • Ликвидность, объемы, транзакции<br/>
            • Фильтрация пулов-пылинок<br/>
            • Ограничение аномальных изменений
          </div>
        </div>

        <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #dee2e6'}}>
          <h4 style={{margin: '0 0 8px 0', color: '#dc3545'}}>4️⃣ Расчет компонентов</h4>
          <div style={{fontSize: '0.9em', lineHeight: 1.4}}>
            <strong>Hybrid Momentum модель:</strong><br/>
            • TX Acceleration - ускорение транзакций<br/>
            • Volume Momentum - импульс объема<br/>
            • Token Freshness - свежесть токена<br/>
            • Orderflow Imbalance - дисбаланс ордеров
          </div>
        </div>

        <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #dee2e6'}}>
          <h4 style={{margin: '0 0 8px 0', color: '#6f42c1'}}>5️⃣ Сглаживание и скор</h4>
          <div style={{fontSize: '0.9em', lineHeight: 1.4}}>
            <strong>EWMA сглаживание:</strong><br/>
            • Стабилизация компонентов<br/>
            • Расчет итогового скора<br/>
            • Сохранение в базу данных
          </div>
        </div>

        <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #dee2e6'}}>
          <h4 style={{margin: '0 0 8px 0', color: '#17a2b8'}}>6️⃣ Отображение</h4>
          <div style={{fontSize: '0.9em', lineHeight: 1.4}}>
            <strong>Фильтрация для дашборда:</strong><br/>
            • Показываем токены с скором ≥ минимума<br/>
            • Сортировка по скору или компонентам<br/>
            • Визуальные индикаторы и фильтры
          </div>
        </div>

        <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #dee2e6'}}>
          <h4 style={{margin: '0 0 8px 0', color: '#6c757d'}}>7️⃣ Архивация</h4>
          <div style={{fontSize: '0.9em', lineHeight: 1.4}}>
            <strong>Управление жизненным циклом:</strong><br/>
            • <code>active</code> → <code>archived</code> при долгом низком скоре<br/>
            • <code>monitoring</code> → <code>archived</code> по таймауту<br/>
            • Освобождение ресурсов системы
          </div>
        </div>

        <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #dee2e6'}}>
          <h4 style={{margin: '0 0 8px 0', color: '#fd7e14'}}>🔄 Обновления</h4>
          <div style={{fontSize: '0.9em', lineHeight: 1.4}}>
            <strong>Периодический пересчет:</strong><br/>
            • Активные токены - каждые 10 сек<br/>
            • Неактивные токены - каждые 60 сек<br/>
            • Адаптивная частота по скору
          </div>
        </div>

      </div>

      <div style={{marginTop: 16, padding: 12, background: '#d1ecf1', border: '1px solid #bee5eb', borderRadius: 4}}>
        <h4 style={{margin: '0 0 8px 0', color: '#0c5460'}}>💡 Ключевые принципы</h4>
        <div style={{fontSize: '0.9em', color: '#0c5460'}}>
          <strong>Автоматизация:</strong> Система работает без вмешательства пользователя<br/>
          <strong>Адаптивность:</strong> Частота обновлений зависит от активности токена<br/>
          <strong>Стабильность:</strong> EWMA сглаживание устраняет шум и ложные сигналы<br/>
          <strong>Эффективность:</strong> Архивация неактивных токенов экономит ресурсы
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
