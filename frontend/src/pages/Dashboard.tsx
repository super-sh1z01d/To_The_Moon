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
  const [statusFilter, setStatusFilter] = useState<{active:boolean, monitoring:boolean, archived:boolean}>({active:true, monitoring:true, archived:false})
  const [pools, setPools] = useState<Record<string, PoolItem[]>>({})
  const [pLoading, setPLoading] = useState<Record<string, boolean>>({})

  async function load(){
    setLoading(true)
    try{
      const statuses = [ statusFilter.active ? 'active' : null, statusFilter.monitoring ? 'monitoring' : null, statusFilter.archived ? 'archived' : null ].filter(Boolean) as string[]
      const res = await getTokens(minScore, limit, offset, sort, statuses)
      setItems(res.items)
      setTotal(res.total)
      // Prefetch pools for visible tokens if not loaded yet
      for(const it of res.items){
        const mint = it.mint_address
        if(!pools[mint] && !pLoading[mint]){
          setPLoading(prev=>({...prev, [mint]: true}))
          getPools(mint).then(data=>{
            setPools(prev=>({...prev, [mint]: data}))
          }).finally(()=>{
            setPLoading(prev=>({...prev, [mint]: false}))
          })
        }
      }
    } finally{ setLoading(false) }
  }
  useEffect(()=>{ load() }, [])

  // Auto-refresh every 5 seconds respecting current filters/pagination
  useEffect(()=>{
    const t = setInterval(()=>{ load() }, 5000)
    return ()=>clearInterval(t)
  }, [minScore, limit, offset, sort, statusFilter])

  // No toggle anymore; pools are prefetched and shown inline

  return (
    <div>
      <div className="toolbar">
        <label>Мин. скор: <input type="number" step={0.01} value={minScore} onChange={e=>setMinScore(Number(e.target.value))}/></label>
        <label>Лимит: <input type="number" min={1} max={100} value={limit} onChange={e=>setLimit(Number(e.target.value))} /></label>
        <label><input type="checkbox" checked={statusFilter.active} onChange={e=>setStatusFilter(s=>({...s, active: e.target.checked}))}/> Активные</label>
        <label><input type="checkbox" checked={statusFilter.monitoring} onChange={e=>setStatusFilter(s=>({...s, monitoring: e.target.checked}))}/> Мониторинг</label>
        <label><input type="checkbox" checked={statusFilter.archived} onChange={e=>setStatusFilter(s=>({...s, archived: e.target.checked}))}/> Архив</label>
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
            <th>Пулы (USDC)</th>
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
                <div className="pools" style={{marginTop: 4}}>
                  {(pools[it.mint_address]||[]).filter(p=> (p.quote||'').toUpperCase()==='SOL' || (p.quote||'').toUpperCase()==='WSOL').map(p=> (
                    <span key={(p.address||'')+ (p.dex||'')+ 'w'} className="pool">{renderDexPill(p)}</span>
                  ))}
                  {(!pools[it.mint_address] || (pools[it.mint_address]||[]).filter(p=> (p.quote||'').toUpperCase()==='SOL' || (p.quote||'').toUpperCase()==='WSOL').length===0) && (pLoading[it.mint_address] ? <span className="muted">Загрузка...</span> : <span className="muted">—</span>)}
                </div>
              </td>
              <td>
                <div className="pools" style={{marginTop: 4}}>
                  {(pools[it.mint_address]||[]).filter(p=> (p.quote||'').toUpperCase()==='USDC').map(p=> (
                    <span key={(p.address||'')+ (p.dex||'')+ 'u'} className="pool">{renderDexPill(p)}</span>
                  ))}
                  {(!pools[it.mint_address] || (pools[it.mint_address]||[]).filter(p=> (p.quote||'').toUpperCase()==='USDC').length===0) && (pLoading[it.mint_address] ? <span className="muted">Загрузка...</span> : <span className="muted">—</span>)}
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
  if(s==='archived') return 'В архиве'
  return s
}

function dexClass(name?: string){
  const slug = (name||'unknown').toLowerCase().replace(/[^a-z0-9]+/g,'-')
  return `pill dex-${slug}`
}

function renderDexPill(p: PoolItem){
  const label = p.dex || '—'
  const cls = dexClass(p.dex)
  if(p.solscan_url){
    return <a className={cls} href={p.solscan_url} target="_blank" rel="noreferrer">{label}</a>
  }
  return <span className={cls}>{label}</span>
}
