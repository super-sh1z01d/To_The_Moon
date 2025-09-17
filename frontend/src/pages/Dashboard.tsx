import { useEffect, useState } from 'react'
import { getTokens, getPools, TokenItem, PoolItem, getActiveModel } from '../lib/api'
import { Link } from 'react-router-dom'
import ScoreCell from '../components/ScoreCell'
import ComponentsCell from '../components/ComponentsCell'
import AgeCell from '../components/AgeCell'
import { formatCalcTime } from '../lib/scoring-utils'

export default function Dashboard(){
  const [minScore, setMinScore] = useState(0)
  const [items, setItems] = useState<TokenItem[]>([])
  const [total, setTotal] = useState(0)
  const [limit, setLimit] = useState(20)
  const [offset, setOffset] = useState(0)
  const [sort, setSort] = useState<'score_desc'|'score_asc'|'tx_desc'|'tx_asc'|'vol_desc'|'vol_asc'|'fresh_desc'|'fresh_asc'|'oi_desc'|'oi_asc'>('score_desc')
  const [loading, setLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState<{active:boolean, monitoring:boolean, archived:boolean}>({active:true, monitoring:true, archived:false})
  const [pools, setPools] = useState<Record<string, PoolItem[]>>({})
  const [pLoading, setPLoading] = useState<Record<string, boolean>>({})
  const [auto, setAuto] = useState(true)
  const [activeModel, setActiveModel] = useState<string>('legacy')
  const [freshOnly, setFreshOnly] = useState(false)
  const [compactMode, setCompactMode] = useState(false)

  async function load(){
    setLoading(true)
    try{
      const statuses = [ statusFilter.active ? 'active' : null, statusFilter.monitoring ? 'monitoring' : null, statusFilter.archived ? 'archived' : null ].filter(Boolean) as string[]
      const res = await getTokens(minScore, limit, offset, sort, statuses)
      
      // Apply fresh-only filter on client side
      let filteredItems = res.items
      if (freshOnly) {
        filteredItems = res.items.filter(item => {
          if (!item.created_at) return false
          const now = new Date()
          const created = new Date(item.created_at)
          const diffHours = (now.getTime() - created.getTime()) / (1000 * 60 * 60)
          return diffHours <= 6 // Fresh threshold of 6 hours
        })
      }
      
      // Apply component-based sorting for hybrid momentum model
      if (activeModel === 'hybrid_momentum' && sort.includes('_')) {
        const [component, direction] = sort.split('_')
        filteredItems = [...filteredItems].sort((a, b) => {
          let aVal = 0, bVal = 0
          
          if (component === 'tx' && a.smoothed_components && b.smoothed_components) {
            aVal = a.smoothed_components.tx_accel
            bVal = b.smoothed_components.tx_accel
          } else if (component === 'vol' && a.smoothed_components && b.smoothed_components) {
            aVal = a.smoothed_components.vol_momentum
            bVal = b.smoothed_components.vol_momentum
          } else if (component === 'fresh' && a.smoothed_components && b.smoothed_components) {
            aVal = a.smoothed_components.token_freshness
            bVal = b.smoothed_components.token_freshness
          } else if (component === 'oi' && a.smoothed_components && b.smoothed_components) {
            aVal = a.smoothed_components.orderflow_imbalance
            bVal = b.smoothed_components.orderflow_imbalance
          }
          
          return direction === 'desc' ? bVal - aVal : aVal - bVal
        })
      }
      
      setItems(filteredItems)
      setTotal(freshOnly ? filteredItems.length : res.total)
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
  useEffect(()=>{ 
    load()
    // Load active scoring model
    getActiveModel().then(model => setActiveModel(model)).catch(() => setActiveModel('legacy'))
  }, [])

  // Load persisted UI state
  useEffect(()=>{
    try{
      const saved = JSON.parse(localStorage.getItem('dash_prefs')||'{}')
      if(saved.minScore!=null) setMinScore(saved.minScore)
      if(saved.limit!=null) setLimit(saved.limit)
      if(saved.sort) setSort(saved.sort)
      if(saved.statusFilter) setStatusFilter(saved.statusFilter)
      if(saved.auto!=null) setAuto(saved.auto)
      if(saved.freshOnly!=null) setFreshOnly(saved.freshOnly)
      if(saved.compactMode!=null) setCompactMode(saved.compactMode)
    }catch{}
  }, [])

  // Persist UI state
  useEffect(()=>{
    const prefs = {minScore, limit, sort, statusFilter, auto, freshOnly, compactMode}
    localStorage.setItem('dash_prefs', JSON.stringify(prefs))
  }, [minScore, limit, sort, statusFilter, auto, freshOnly, compactMode])

  // Auto-refresh every 5 seconds respecting current filters/pagination
  useEffect(()=>{
    if(!auto) return
    const t = setInterval(()=>{ load() }, 5000)
    return ()=>clearInterval(t)
  }, [auto, minScore, limit, offset, sort, statusFilter, freshOnly])

  // No toggle anymore; pools are prefetched and shown inline

  return (
    <div>
      <div className="toolbar">
        <label>Мин. скор: <input type="number" step={0.01} value={minScore} onChange={e=>setMinScore(Number(e.target.value))}/></label>
        <label>Лимит: <input type="number" min={1} max={100} value={limit} onChange={e=>setLimit(Number(e.target.value))} /></label>
        <label><input type="checkbox" checked={statusFilter.active} onChange={e=>setStatusFilter(s=>({...s, active: e.target.checked}))}/> Активные</label>
        <label><input type="checkbox" checked={statusFilter.monitoring} onChange={e=>setStatusFilter(s=>({...s, monitoring: e.target.checked}))}/> Мониторинг</label>
        <label><input type="checkbox" checked={statusFilter.archived} onChange={e=>setStatusFilter(s=>({...s, archived: e.target.checked}))}/> Архив</label>
        <label><input type="checkbox" checked={freshOnly} onChange={e=>setFreshOnly(e.target.checked)} /> Только свежие</label>
        <label><input type="checkbox" checked={compactMode} onChange={e=>setCompactMode(e.target.checked)} /> Компактный режим</label>
        <label><input type="checkbox" checked={auto} onChange={e=>setAuto(e.target.checked)} /> Автообновление</label>
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
            <th title="Имя/символ из DexScreener или миграций">Название (Символ)</th>
            <th style={{cursor:'pointer'}} title="Сглаженный скор (экспоненциальное скользящее среднее для снижения волатильности)" onClick={()=>{ setSort(sort==='score_desc'?'score_asc':'score_desc'); setTimeout(load,0) }}>
              Скор* {sort==='score_desc'?'↓':sort==='score_asc'?'↑':''}
            </th>
            {activeModel === 'hybrid_momentum' && (
              <>
                <th style={{cursor:'pointer'}} title="Transaction Acceleration - ускорение транзакционной активности" onClick={()=>{ setSort(sort==='tx_desc'?'tx_asc':'tx_desc'); setTimeout(load,0) }}>
                  TX {sort==='tx_desc'?'↓':sort==='tx_asc'?'↑':''}
                </th>
                <th style={{cursor:'pointer'}} title="Volume Momentum - импульс торгового объема" onClick={()=>{ setSort(sort==='vol_desc'?'vol_asc':'vol_desc'); setTimeout(load,0) }}>
                  Vol {sort==='vol_desc'?'↓':sort==='vol_asc'?'↑':''}
                </th>
                <th style={{cursor:'pointer'}} title="Token Freshness - бонус за свежесть токена" onClick={()=>{ setSort(sort==='fresh_desc'?'fresh_asc':'fresh_desc'); setTimeout(load,0) }}>
                  Fresh {sort==='fresh_desc'?'↓':sort==='fresh_asc'?'↑':''}
                </th>
                <th style={{cursor:'pointer'}} title="Orderflow Imbalance - дисбаланс покупок/продаж" onClick={()=>{ setSort(sort==='oi_desc'?'oi_asc':'oi_desc'); setTimeout(load,0) }}>
                  OI {sort==='oi_desc'?'↓':sort==='oi_asc'?'↑':''}
                </th>
                <th title="Возраст токена с индикатором свежести">Возраст</th>
              </>
            )}
            <th title="Сумма ликвидности по пулам WSOL/SOL и USDC">Ликвидность (USD)</th>
            <th>Статус</th>
            <th title="Ссылки на Solscan пулов SOL/WSOL">Пулы (WSOL)</th>
            <th title="Ссылки на Solscan пулов USDC">Пулы (USDC)</th>
            <th title="Время расчёта скора">Расчёт</th>
            <th>Solscan</th>
          </tr>
        </thead>
        <tbody>
          {items.map(it=> (
            <tr key={it.mint_address} className={it.status==='archived' ? 'row-archived' : ''}>
              <td><Link to={`/token/${it.mint_address}`}>{it.name || '—'}</Link> <span className="muted">({it.symbol || ''})</span></td>
              <td>
                <ScoreCell 
                  score={it.score} 
                  components={it.smoothed_components} 
                  model={it.scoring_model || activeModel} 
                />
              </td>
              {activeModel === 'hybrid_momentum' && (
                <>
                  <td>{it.smoothed_components ? it.smoothed_components.tx_accel.toFixed(3) : '—'}</td>
                  <td>{it.smoothed_components ? it.smoothed_components.vol_momentum.toFixed(3) : '—'}</td>
                  <td>{it.smoothed_components ? it.smoothed_components.token_freshness.toFixed(3) : '—'}</td>
                  <td>{it.smoothed_components ? it.smoothed_components.orderflow_imbalance.toFixed(3) : '—'}</td>
                  <td><AgeCell createdAt={it.created_at} /></td>
                </>
              )}
              <td>{it.liquidity_usd ? ('$'+Number(it.liquidity_usd).toLocaleString()) : '—'}</td>
              <td>{statusBadge(it.status)}</td>
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
              <td>{formatCalcTime(it.scored_at)}</td>
              <td><a href={it.solscan_url} target="_blank" rel="noreferrer">Открыть</a></td>
          </tr>
        ))}
      </tbody>
    </table>
    <div style={{marginTop: '8px', fontSize: '0.85em', color: '#666', fontStyle: 'italic'}}>
      * Скоры сглажены для снижения волатильности (экспоненциальное скользящее среднее)
    </div>
  </div>
  )
}


function statusLabel(s?: string){
  if(!s) return '—'
  if(s==='active') return 'Активен'
  if(s==='monitoring') return 'Мониторинг'
  if(s==='archived') return 'В архиве'
  return s
}

function statusBadge(s?: string){
  const label = statusLabel(s)
  const cls = `status-badge ${s ? 'status-'+s : ''}`
  return <span className={cls}>{label}</span>
}

function renderCalc(it: TokenItem){
  const f = it.fetched_at ? fmtDate(it.fetched_at) : '—'
  const s = it.scored_at ? fmtDate(it.scored_at) : '—'
  return <span className="muted" title={`Dex: ${it.fetched_at||'-'}\nScore: ${it.scored_at||'-'}`}>Dex: {f} / Score: {s}</span>
}

function fmtDate(iso: string){
  try{
    const d = new Date(iso)
    const y = d.getFullYear()
    const m = String(d.getMonth()+1).padStart(2,'0')
    const da = String(d.getDate()).padStart(2,'0')
    const hh = String(d.getHours()).padStart(2,'0')
    const mm = String(d.getMinutes()).padStart(2,'0')
    return `${y}-${m}-${da} ${hh}:${mm}`
  }catch{ return iso }
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
