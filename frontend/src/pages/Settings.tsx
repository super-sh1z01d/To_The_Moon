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
          </section>
          <section>
            <h3>Пороги</h3>
            <Field label="Минимальное значение скора (τ)" hint="Токены ниже порога не отображаются на дашборде" k="min_score" v={vals['min_score']} set={update} />
          </section>
          <section>
            <h3>Тайминги и жизненный цикл</h3>
            <Field label="Интервал для горячих (сек)" hint="Частота обновлений для токенов с высоким скором" k="hot_interval_sec" v={vals['hot_interval_sec']} set={update} />
            <Field label="Интервал для остывших (сек)" hint="Частота обновлений для токенов с низким скором" k="cold_interval_sec" v={vals['cold_interval_sec']} set={update} />
            <Field label="Период неактивности для архивации (час)" hint="Сколько часов подряд скор ниже порога, чтобы архивировать" k="archive_below_hours" v={vals['archive_below_hours']} set={update} />
            <Field label="Таймаут мониторинга (час)" hint="Через сколько часов мониторинг без активации — архив" k="monitoring_timeout_hours" v={vals['monitoring_timeout_hours']} set={update} />
            <Field label="Мин. ликвидность внешнего пула для активации (USD)" hint="Монета активируется при наличии внешнего пула (не pumpswap/pumpfun) с ликвидностью ≥ этого порога; при падении ниже — возвращается в мониторинг" k="activation_min_liquidity_usd" v={vals['activation_min_liquidity_usd']} set={update} />
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
