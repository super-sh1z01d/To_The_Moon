import { useEffect, useState } from 'react'
import { getDefaultSettings, getSettings, putSetting, recalc, SettingsMap } from '../lib/api'

const keys = [
  'weight_s','weight_l','weight_m','weight_t',
  'min_score','score_smoothing_alpha','min_pool_liquidity_usd','max_price_change_5m','min_score_change','max_liquidity_change_ratio',
  'hot_interval_sec','cold_interval_sec','archive_below_hours','monitoring_timeout_hours',
  'activation_min_liquidity_usd'
]

export default function Settings(){
  const [vals, setVals] = useState<SettingsMap>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string>('')

  useEffect(()=>{ (async()=>{
    setLoading(true)
    try{ setVals(await getSettings()) } finally{ setLoading(false) }
  })() }, [])

  const update = (k: string, v: string) => setVals(prev=>({...prev, [k]: v}))

  async function save(recalculate: boolean){
    setSaving(true); setMessage('')
    try{
      for(const k of keys){
        if(vals[k] != null){ await putSetting(k, String(vals[k])) }
      }
      if(recalculate){ await recalc() }
      setMessage(recalculate ? 'Сохранено. Пересчёт запущен.' : 'Сохранено.')
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
          <section>
            <h3>Весовые коэффициенты</h3>
            <Field label="Вес волатильности (W_s)" type="number" hint="Определяет важность краткосрочной активности цены" k="weight_s" v={vals['weight_s']} set={update} />
            <Field label="Вес ликвидности (W_l)" type="number" hint="Отражает устойчивость актива и глубину рынка" k="weight_l" v={vals['weight_l']} set={update} />
            <Field label="Вес импульса (W_m)" type="number" hint="Соотношение движений 5м/15м для выявления импульса" k="weight_m" v={vals['weight_m']} set={update} />
            <Field label="Вес частоты торгов (W_t)" type="number" hint="Число сделок как прокси интереса трейдеров" k="weight_t" v={vals['weight_t']} set={update} />
            <WeightsSum ws={vals['weight_s']} wl={vals['weight_l']} wm={vals['weight_m']} wt={vals['weight_t']} />
            <Formula />
          </section>
          <section>
            <h3>Пороги</h3>
            <Field label="Минимальное значение скора (τ)" type="number" hint="Токены ниже порога не отображаются на дашборде" k="min_score" v={vals['min_score']} set={update} />
          </section>
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

function Formula(){
  return (
    <div style={{marginTop:8}}>
      <h4 style={{margin:'8px 0'}}>Формула скоринга</h4>
      <pre style={{whiteSpace:'pre-wrap', background:'#fafafa', border:'1px solid #eee', padding:8, borderRadius:4}}>
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
