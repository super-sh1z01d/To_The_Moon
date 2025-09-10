import { useEffect, useState } from 'react'
import { getSettings, putSetting, recalc, SettingsMap } from '../lib/api'

const keys = [
  'weight_s','weight_l','weight_m','weight_t',
  'min_score','hot_interval_sec','cold_interval_sec','archive_below_hours','monitoring_timeout_hours',
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

  return (
    <div>
      <h2>Настройки</h2>
      {loading ? <p>Загрузка...</p> : (
        <div className="settings">
          <section>
            <h3>Весовые коэффициенты</h3>
            <Field label="Вес волатильности (W_s)" hint="Определяет важность краткосрочной активности цены" k="weight_s" v={vals['weight_s']} set={update} />
            <Field label="Вес ликвидности (W_l)" hint="Отражает устойчивость актива и глубину рынка" k="weight_l" v={vals['weight_l']} set={update} />
            <Field label="Вес импульса (W_m)" hint="Соотношение движений 5м/15м для выявления импульса" k="weight_m" v={vals['weight_m']} set={update} />
            <Field label="Вес частоты торгов (W_t)" hint="Число сделок как прокси интереса трейдеров" k="weight_t" v={vals['weight_t']} set={update} />
            <Formula />
          </section>
          <section>
            <h3>Пороги</h3>
            <Field label="Минимальное значение скора (τ)" hint="Токены ниже порога не отображаются на дашборде" k="min_score" v={vals['min_score']} set={update} />
          </section>
          <section>
            <h3>Тайминги и жизненный цикл</h3>
            <Field label="Интервал для горячих (сек)" hint="Статус: active с последним скором ≥ τ (min_score). Частота обновлений метрик/скора для таких токенов." k="hot_interval_sec" v={vals['hot_interval_sec']} set={update} />
            <Field label="Интервал для остывших (сек)" hint="Статус: active с последним скором < τ либо без скора. Обновляются реже, чтобы экономить лимиты." k="cold_interval_sec" v={vals['cold_interval_sec']} set={update} />
            <Field label="Период неактивности для архивации (час)" hint="Статус: active → archived, если в течение этого периода ни разу не было скора ≥ τ." k="archive_below_hours" v={vals['archive_below_hours']} set={update} />
            <Field label="Таймаут мониторинга (час)" hint="Статус: monitoring → archived, если за этот период не выполнены условия активации." k="monitoring_timeout_hours" v={vals['monitoring_timeout_hours']} set={update} />
            <Field label="Мин. ликвидность внешнего пула для активации (USD)" hint="Статусы: monitoring↔active. Активируем при наличии внешнего пула WSOL/SOL/USDC (не pumpfun/pumpswap/pumpfun-amm) с ликвидностью ≥ порога; при отсутствии — возвращаем в monitoring." k="activation_min_liquidity_usd" v={vals['activation_min_liquidity_usd']} set={update} />
          </section>
          <div className="actions">
            <button disabled={saving} onClick={()=>save(false)}>{saving? 'Сохранение...' : 'Сохранить'}</button>
            <button disabled={saving} onClick={()=>save(true)}>{saving? '...' : 'Сохранить и Пересчитать'}</button>
            {message && <span className="muted" style={{marginLeft: 8}}>{message}</span>}
          </div>
        </div>
      )}
    </div>
  )
}

function Field({label, hint, k, v, set}:{label:string, hint?:string, k:string,v?:string,set:(k:string,v:string)=>void}){
  return (
    <label className="field" title={hint}>
      <span>{label}</span>
      <input value={v??''} onChange={e=>set(k, e.target.value)} title={hint} />
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
- s = clip(|ΔP_5m| / 0.1)
- m = clip(|ΔP_5м| / (|ΔP_15м| + 0.001))
- t = clip((N_5м / 5) / 300)
- clip(x) = min(max(x, 0), 1)

Примечания:
- L_tot — суммарная ликвидность по WSOL/SOL/USDC пулам (без classic pumpfun).
- ΔP берётся по самой ликвидной паре; если m15 отсутствует, используется h1/4.
- N_5м — сумма (buys+sells) за 5 минут по всем учтённым пулам.
      </pre>
    </div>
  )
}
