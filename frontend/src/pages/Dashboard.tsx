import { useEffect, useState } from 'react'
import { getTokens, getPools, TokenItem, PoolItem } from '../lib/api'
import { Link } from 'react-router-dom'

export default function Dashboard(){
  const [minScore, setMinScore] = useState(0)
  const [items, setItems] = useState<TokenItem[]>([])
  const [total, setTotal] = useState(0)
  const [limit, setLimit] = useState(20)
  const [offset, setOffset] = useState(0)
  const [sort, setSort] = useState<'score_desc'|'score_asc'>('score_desc')
  const [loading, setLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState<{active:boolean, monitoring:boolean}>({active:true, monitoring:true})
  const [pools, setPools] = useState<Record<string, PoolItem[]>>({})
  const [pLoading, setPLoading] = useState<Record<string, boolean>>({})

  async function load(){
    setLoading(true)
    try{
      const statuses = [ statusFilter.active ? 'active' : null, statusFilter.monitoring ? 'monitoring' : null ].filter(Boolean) as string[]
      const res = await getTokens(minScore, limit, offset, sort, statuses)
      setItems(res.items)
      setTotal(res.total)
    } finally{ setLoading(false) }
  }
  useEffect(()=>{ load() }, [])

  async function togglePools(mint: string){
    const opened = pools[mint]
    if(opened){
      setPools(prev=>{ const n={...prev}; delete n[mint]; return n })
      return
    }
    setPLoading(prev=>({...prev, [mint]: true}))
    try{
      const data = await getPools(mint)
      setPools(prev=>({...prev, [mint]: data}))
    } finally{
      setPLoading(prev=>({...prev, [mint]: false}))
    }
  }

  return (
    <div>
      <div className="toolbar">
        <label>Мин. скор: <input type="number" step={0.01} value={minScore} onChange={e=>setMinScore(Number(e.target.value))}/></label>
        <label>Лимит: <input type="number" min={1} max={100} value={limit} onChange={e=>setLimit(Number(e.target.value))} /></label>
        <label><input type="checkbox" checked={statusFilter.active} onChange={e=>setStatusFilter(s=>({...s, active: e.target.checked}))}/> Активные</label>
        <label><input type="checkbox" checked={statusFilter.monitoring} onChange={e=>setStatusFilter(s=>({...s, monitoring: e.target.checked}))}/> Мониторинг</label>
        <button onClick={()=>{ setOffset(0); load() }} disabled={loading}>{loading? 'Загрузка...' : 'Обновить'}</button>
        <div style={{marginLeft: 'auto'}}>
          <button disabled={offset===0 || loading} onClick={()=>{ setOffset(Math.max(0, offset-limit)); setTimeout(load,0) }}>←</button>
          <span style={{margin:'0 8px'}}>{offset+1}–{Math.min(offset+limit, total)} из {total}</span>
          <button disabled={(offset+limit)>=total || loading} onClick={()=>{ setOffset(offset+limit); setTimeout(load,0) }}>→</button>
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Название (Символ)</th>
            <th style={{cursor:'pointer'}} onClick={()=>{ setSort(sort==='score_desc'?'score_asc':'score_desc'); setTimeout(load,0) }}>
              Скор {sort==='score_desc'?'↓':'↑'}
            </th>
            <th>Ликвидность (USD)</th>
            <th>Δ 5м / 15м</th>
            <th>Транз. 5м</th>
            <th>Статус</th>
            <th>Пулы (WSOL)</th>
            <th>Solscan</th>
          </tr>
        </thead>
        <tbody>
          {items.map(it=> (
            <tr key={it.mint_address}>
              <td><Link to={`/token/${it.mint_address}`}>{it.name || '—'}</Link> <span className="muted">({it.symbol || ''})</span></td>
              <td>{it.score ?? '—'}</td>
              <td>{it.liquidity_usd ? ('$'+Number(it.liquidity_usd).toLocaleString()) : '—'}</td>
              <td><span className={pctClass(it.delta_p_5m)}>{fmtPct(it.delta_p_5m)}</span> / <span className={pctClass(it.delta_p_15m)}>{fmtPct(it.delta_p_15m)}</span></td>
              <td>{it.n_5m ?? '—'}</td>
              <td>{statusLabel(it.status)}</td>
              <td>
                <button onClick={()=>togglePools(it.mint_address)} disabled={pLoading[it.mint_address]}>Пулы</button>
                <div className="pools">
                  {(pools[it.mint_address]||[]).map(p=> (
                    <span key={(p.address||'')+ (p.dex||'')} className="pool">
                      {p.address ? <a href={p.solscan_url!} target="_blank" rel="noreferrer">{p.address}</a> : '—'}
                      <span className="pill">{p.dex || '—'}</span>
                    </span>
                  ))}
                  {pLoading[it.mint_address] ? <span className="muted">Загрузка...</span> : null}
                </div>
              </td>
              <td><a href={it.solscan_url} target="_blank" rel="noreferrer">Открыть</a></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function fmtPct(x?: number){
  if(x==null) return '—'
  return (x*100).toFixed(2)+'%'
}
function pctClass(x?: number){
  if(x==null) return ''
  return x>0 ? 'pos' : x<0 ? 'neg' : ''
}
function statusLabel(s?: string){
  if(!s) return '—'
  if(s==='active') return 'Активен'
  if(s==='monitoring') return 'Мониторинг'
  return s
}
