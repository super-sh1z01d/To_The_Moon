import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { PoolItem } from '../lib/api'

type TokenDetail = {
  mint_address: string
  name?: string
  symbol?: string
  status: string
  score?: number
  metrics?: Record<string, any>
  score_history: { created_at: string, score?: number }[]
  pools?: PoolItem[]
  solscan_url: string
}

export default function TokenDetail(){
  const { mint } = useParams()
  const [data, setData] = useState<TokenDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')

  useEffect(()=>{ (async()=>{
    if(!mint) return
    setLoading(true); setError('')
    try{
      const r = await fetch(`/tokens/${mint}`)
      if(!r.ok) throw new Error('failed to load')
      setData(await r.json())
    }catch(e:any){ setError(e.message || 'error') }
    finally{ setLoading(false) }
  })() }, [mint])

  const points = useMemo(()=> (data?.score_history||[]).slice().reverse().map(h=> (h.score ?? 0)), [data])

  return (
    <div>
      {loading && <div className="spinner">Загрузка...</div>}
      {error && <div className="error">Ошибка: {error}</div>}
      {data && (
        <div>
          <h2>{data.name||'—'} <span className="muted">({data.symbol||''})</span></h2>
          <div className="kv">
            <div><b>Mint:</b> {data.mint_address}</div>
            <div><b>Статус:</b> <span className={`status-badge ${'status-'+data.status}`}>{statusLabel(data.status)}</span></div>
            <div><b>Скор:</b> {fmtNum(data.score)}</div>
            <div><a href={data.solscan_url} target="_blank" rel="noreferrer">Открыть в Solscan</a></div>
          </div>
          <section>
            <h3>Динамика скора</h3>
            {points.length>0 ? <Sparkline data={points} width={360} height={80}/> : <div className="muted">Нет данных</div>}
          </section>
          <section>
            <h3>Последние метрики</h3>
            <table>
              <tbody>
                <tr><td>Ликвидность (USD)</td><td>{fmtMoney(data.metrics?.L_tot)}</td></tr>
                <tr><td>Δ 5м</td><td className={pctClass(data.metrics?.delta_p_5m)}>{fmtPct(data.metrics?.delta_p_5m)}</td></tr>
                <tr><td>Δ 15м</td><td className={pctClass(data.metrics?.delta_p_15m)}>{fmtPct(data.metrics?.delta_p_15m)}</td></tr>
                <tr><td>Транзакции 5м</td><td>{fmtInt(data.metrics?.n_5m)}</td></tr>
                <tr><td>Основной DEX</td><td>{data.metrics?.primary_dex || '—'}</td></tr>
              </tbody>
            </table>
          </section>
          <section>
            <h3>WSOL‑пулы</h3>
            <div className="pools">
              {(data.pools||[]).length === 0 && <div className="muted">Нет данных</div>}
              {(data.pools||[]).map(p=> (
                <span key={(p.address||'')+(p.dex||'')} className="pool">
                  {p.address ? <a href={p.solscan_url!} target="_blank" rel="noreferrer">{p.address}</a> : '—'}
                  <span className="pill">{p.dex || '—'}</span>
                </span>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

function statusLabel(s: string){
  if(s==='active') return 'Активен'
  if(s==='monitoring') return 'Мониторинг'
  if(s==='archived') return 'В архиве'
  return s
}

function fmtNum(x?: number){ return x==null ? '—' : String(x) }
function fmtInt(x?: number){ return x==null ? '—' : Number(x).toLocaleString() }
function fmtMoney(x?: number){ return x==null ? '—' : '$'+Number(x).toLocaleString() }
function fmtPct(x?: number){ return x==null ? '—' : (x*100).toFixed(2)+'%' }
function pctClass(x?: number){ if(x==null) return ''; return x>0 ? 'pos' : x<0 ? 'neg' : '' }

function Sparkline({data, width, height}:{data:number[], width:number, height:number}){
  if(data.length === 0) return null
  const min = Math.min(...data)
  const max = Math.max(...data)
  const pad = 2
  const w = width - pad*2
  const h = height - pad*2
  const rng = (max-min)||1
  const step = w/(data.length-1||1)
  const points = data.map((v,i)=> {
    const x = pad + i*step
    const y = pad + h - ((v-min)/rng)*h
    return `${x},${y}`
  }).join(' ')
  return (
    <svg width={width} height={height} className="spark">
      <polyline fill="none" stroke="#4caf50" strokeWidth="2" points={points} />
    </svg>
  )
}
