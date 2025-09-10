import { useEffect, useMemo, useState } from 'react'
import { getLogs, getLogsMeta, LogEntry } from '../lib/api'

const LEVELS = ['DEBUG','INFO','WARNING','ERROR','CRITICAL']

export default function Logs(){
  const [availableLoggers, setAvailableLoggers] = useState<string[]>([])
  const [selectedLoggers, setSelectedLoggers] = useState<Record<string, boolean>>({})
  const [levels, setLevels] = useState<Record<string, boolean>>({INFO:true, WARNING:true, ERROR:true})
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(200)
  const [items, setItems] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [autorefresh, setAutorefresh] = useState(true)

  async function load(){
    setLoading(true)
    try{
      const lv = Object.keys(levels).filter(k=>levels[k])
      const lg = Object.keys(selectedLoggers).filter(k=>selectedLoggers[k])
      const data = await getLogs({limit, levels: lv, loggers: lg, contains: query || undefined})
      setItems(data)
    } finally{ setLoading(false) }
  }

  useEffect(()=>{ (async()=>{
    try{
      const meta = await getLogsMeta()
      setAvailableLoggers(meta.loggers)
      // Initialize logger filter map if empty
      if(Object.keys(selectedLoggers).length===0){
        const init: Record<string, boolean> = {}
        for(const l of meta.loggers){ init[l] = true }
        setSelectedLoggers(init)
      }
    } catch{}
    load()
  })() }, [])

  useEffect(()=>{
    if(!autorefresh) return
    const t = setInterval(()=>{ load() }, 2000)
    return ()=>clearInterval(t)
  }, [autorefresh, limit, levels, selectedLoggers, query])

  const levelList = useMemo(()=> Object.keys(levels).filter(k=>levels[k]), [levels])
  const loggerList = useMemo(()=> Object.keys(selectedLoggers).filter(k=>selectedLoggers[k]), [selectedLoggers])

  return (
    <div>
      <div className="toolbar">
        <label>Поиск: <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="строка в сообщении" /></label>
        <label>Лимит: <input type="number" min={10} max={500} value={limit} onChange={e=>setLimit(Number(e.target.value))} /></label>
        <label><input type="checkbox" checked={autorefresh} onChange={e=>setAutorefresh(e.target.checked)} /> Автообновление</label>
        <button onClick={load} disabled={loading}>{loading? 'Загрузка...' : 'Обновить'}</button>
      </div>

      <div className="kv">
        <div>
          <b>Уровни</b>
          <div>
            {LEVELS.map(l=> (
              <label key={l} style={{marginRight:8}}>
                <input type="checkbox" checked={!!levels[l]} onChange={e=>setLevels(prev=>({...prev, [l]: e.target.checked}))} /> {l}
              </label>
            ))}
          </div>
        </div>
        <div>
          <b>Процессы</b>
          <div style={{maxHeight:120, overflow:'auto', border:'1px solid #ddd', padding:6}}>
            {availableLoggers.length===0 && <div className="muted">Нет данных</div>}
            {availableLoggers.map(l=> (
              <label key={l} style={{display:'inline-block', marginRight:8}}>
                <input type="checkbox" checked={selectedLoggers[l]===undefined ? true : !!selectedLoggers[l]}
                  onChange={e=>setSelectedLoggers(prev=>({...prev, [l]: e.target.checked}))} /> {l}
              </label>
            ))}
          </div>
        </div>
        <div>
          <div className="muted">Фильтров применено: уровни {levelList.join(', ')||'—'}, процессы {loggerList.join(', ')||'—'}</div>
        </div>
      </div>

      <table>
        <thead>
          <tr>
            <th style={{width:220}}>Время</th>
            <th style={{width:110}}>Уровень</th>
            <th style={{width:200}}>Процесс</th>
            <th>Сообщение</th>
          </tr>
        </thead>
        <tbody>
          {items.map((e, idx)=> (
            <tr key={idx}>
              <td><code>{e.ts}</code></td>
              <td>{e.level}</td>
              <td>{e.logger}</td>
              <td>
                <div>{e.msg}</div>
                <div className="muted" style={{fontSize:12}}>{summarize(e)}</div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function summarize(e: LogEntry){
  const omit = new Set(['ts','level','logger','msg','module','func','line'])
  const parts: string[] = []
  for(const [k,v] of Object.entries(e)){
    if(omit.has(k)) continue
    if(v==null) continue
    const s = typeof v === 'object' ? JSON.stringify(v) : String(v)
    parts.push(`${k}=${s}`)
  }
  return parts.join(' | ')
}

